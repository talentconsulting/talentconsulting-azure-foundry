import json
import unittest

from workflow import WorkflowError, merge_schemas, parse_workflow_request, run_workflow, validate_schema


SOURCE = "https://github.com/source/app/tree/main/src/Data"
FILE = "https://github.com/source/app/blob/main/src/Data/Orders.cs"
DISCOVERY = {"schemaFiles": [FILE], "excludedFiles": []}
SCHEMA = {
    "database": {"name": "app", "engine": None},
    "tables": [{"name": "orders", "schema": "dbo"}],
    "types": [],
}


def _table_schema(name: str, schema: str = None) -> dict:
    return {
        "database": {"name": "app", "engine": None},
        "tables": [{"name": name, "schema": schema}],
        "types": [],
    }


class WorkflowTests(unittest.TestCase):
    def test_input_requires_destination_repository_for_direct_publication(self):
        with self.assertRaisesRegex(WorkflowError, "targetRepository"):
            parse_workflow_request(json.dumps({"sourceUrl": SOURCE}))

    def test_deferred_workflow_generates_once_without_publishing(self):
        calls = []

        def invoke(project, name, model, payload, max_attempts=2):
            calls.append((name, payload, max_attempts))
            if name == "discovery":
                self.assertEqual({"sourceUrl": SOURCE}, payload)
                return DISCOVERY
            self.assertEqual("generator", name)
            self.assertEqual({"sourceUrl": SOURCE, "sourceFiles": [FILE]}, payload)
            return SCHEMA

        result = run_workflow(
            object(),
            {"sourceUrl": SOURCE, "deferPublication": True},
            "discovery", "generator",
            "publisher",
            "gpt-4o",
            invoker=invoke,
        )

        self.assertTrue(result["success"])
        self.assertEqual(1, result["generatedSchemaCount"])
        self.assertEqual(["discovery", "generator"], [call[0] for call in calls])
        self.assertEqual({"sourceUrl": SOURCE, "schema": SCHEMA}, result["schemas"][0])

    def test_direct_workflow_generates_and_publishes_once(self):
        calls = []

        def invoke(project, name, model, payload, max_attempts=2):
            calls.append((name, payload, max_attempts))
            if name == "discovery":
                return DISCOVERY
            if name == "generator":
                return SCHEMA
            self.assertEqual(1, max_attempts)
            self.assertEqual("target/schemas", payload["repository"])
            self.assertEqual("app/db-schema/database.schema.json", payload["schemas"][0]["targetPath"])
            return {"success": True, "status": "created"}

        result = run_workflow(
            object(),
            {"sourceUrl": SOURCE, "targetRepository": "target/schemas"},
            "discovery", "generator",
            "publisher",
            "gpt-4o",
            invoker=invoke,
        )

        self.assertTrue(result["success"])
        self.assertEqual(["discovery", "generator", "publisher"], [call[0] for call in calls])

    def test_explicit_target_directory_is_used(self):
        def invoke(project, name, model, payload, max_attempts=2):
            if name == "discovery":
                return DISCOVERY
            if name == "generator":
                return SCHEMA
            self.assertEqual("custom/db/database.schema.json", payload["schemas"][0]["targetPath"])
            return {"success": True}

        result = run_workflow(
            object(),
            {"sourceUrl": SOURCE, "targetRepository": "target/schemas", "targetDirectory": "custom/db"},
            "discovery", "generator",
            "publisher",
            "gpt-4o",
            invoker=invoke,
        )
        self.assertTrue(result["success"])

    def test_generation_failure_does_not_publish(self):
        calls = []

        def invoke(project, name, model, payload, max_attempts=2):
            calls.append(name)
            if name == "discovery":
                return DISCOVERY
            return {"error": {"code": "no_database_sources", "message": "No database sources found."}}

        result = run_workflow(
            object(),
            {"sourceUrl": SOURCE, "targetRepository": "target/schemas"},
            "discovery", "generator",
            "publisher",
            "gpt-4o",
            invoker=invoke,
        )
        self.assertFalse(result["success"])
        self.assertEqual(["discovery", "generator", "generator", "generator"], calls)
        self.assertEqual(0, result["generatedSchemaCount"])

    def test_a_transient_batch_failure_is_retried_before_giving_up(self):
        discovery = {"schemaFiles": [FILE], "excludedFiles": []}
        attempts = []

        def invoke(project, name, model, payload, max_attempts=2):
            if name == "discovery":
                return discovery
            attempts.append(name)
            if len(attempts) < 2:
                return {"error": {"code": "invalid_model_output", "message": "tables[0].columns[0].type must be non-empty."}}
            return SCHEMA

        result = run_workflow(
            object(),
            {"sourceUrl": SOURCE, "deferPublication": True},
            "discovery", "generator",
            "publisher",
            "gpt-4o",
            invoker=invoke,
        )

        self.assertTrue(result["success"])
        self.assertEqual(2, len(attempts))

    def test_generator_is_called_once_per_batch_and_results_are_merged(self):
        files = [f"https://github.com/source/app/blob/main/src/Data/Table{index}.cs" for index in range(7)]
        discovery = {"schemaFiles": files, "excludedFiles": []}
        generator_calls = []

        def invoke(project, name, model, payload, max_attempts=2):
            if name == "discovery":
                return discovery
            self.assertEqual("generator", name)
            generator_calls.append(payload["sourceFiles"])
            return _table_schema(f"table_{len(generator_calls)}")

        result = run_workflow(
            object(),
            {"sourceUrl": SOURCE, "deferPublication": True},
            "discovery", "generator",
            "publisher",
            "gpt-4o",
            generator_batch_size=3,
            invoker=invoke,
        )

        self.assertTrue(result["success"])
        self.assertEqual([files[0:3], files[3:6], files[6:7]], generator_calls)
        self.assertEqual(3, len(result["schemas"][0]["schema"]["tables"]))

    def test_a_cross_batch_name_collision_keeps_the_first_table_and_still_succeeds(self):
        files = [f"https://github.com/source/app/blob/main/src/Data/Table{index}.cs" for index in range(6)]
        discovery = {"schemaFiles": files, "excludedFiles": []}
        generator_calls = []

        def invoke(project, name, model, payload, max_attempts=2):
            if name == "discovery":
                return discovery
            generator_calls.append(payload["sourceFiles"])
            # both batches independently report a table named "orders" (a mis-extraction in one of them)
            return _table_schema("orders")

        result = run_workflow(
            object(),
            {"sourceUrl": SOURCE, "deferPublication": True},
            "discovery", "generator",
            "publisher",
            "gpt-4o",
            generator_batch_size=3,
            invoker=invoke,
        )

        self.assertTrue(result["success"])
        self.assertEqual(1, len(result["schemas"][0]["schema"]["tables"]))
        self.assertEqual(1, len(result["generationErrors"]))
        self.assertEqual("DuplicateTable", result["generationErrors"][0]["errorType"])

    def test_a_batch_that_fails_every_retry_does_not_block_the_others(self):
        files = [f"https://github.com/source/app/blob/main/src/Data/Table{index}.cs" for index in range(6)]
        discovery = {"schemaFiles": files, "excludedFiles": []}
        generator_calls = []

        def invoke(project, name, model, payload, max_attempts=2):
            if name == "discovery":
                return discovery
            generator_calls.append(payload["sourceFiles"])
            if payload["sourceFiles"] == files[3:6]:
                return {"error": {"code": "invalid_model_output", "message": "tables[0] has an invalid shape."}}
            return _table_schema("table_ok")

        result = run_workflow(
            object(),
            {"sourceUrl": SOURCE, "deferPublication": True},
            "discovery", "generator",
            "publisher",
            "gpt-4o",
            generator_batch_size=3,
            invoker=invoke,
        )

        self.assertTrue(result["success"])
        self.assertEqual(1, len(result["schemas"][0]["schema"]["tables"]))
        self.assertEqual(1, len(result["generationErrors"]))
        self.assertEqual(files[3:6], result["generationErrors"][0]["files"])
        self.assertIn("invalid shape", result["generationErrors"][0]["message"])
        # the failed batch is retried 3 times; the healthy batch only needs 1 call
        self.assertEqual(4, len(generator_calls))

    def test_every_batch_failing_reports_each_batch_and_does_not_publish(self):
        files = [f"https://github.com/source/app/blob/main/src/Data/Table{index}.cs" for index in range(6)]
        discovery = {"schemaFiles": files, "excludedFiles": []}

        def invoke(project, name, model, payload, max_attempts=2):
            if name == "discovery":
                return discovery
            return {"error": {"code": "invalid_model_output", "message": "tables[0] has an invalid shape."}}

        result = run_workflow(
            object(),
            {"sourceUrl": SOURCE, "deferPublication": True},
            "discovery", "generator",
            "publisher",
            "gpt-4o",
            generator_batch_size=3,
            invoker=invoke,
        )

        self.assertFalse(result["success"])
        self.assertEqual([files[0:3], files[3:6]], [error["files"] for error in result["generationErrors"]])

    def test_merge_schemas_combines_tables_and_types_and_fills_in_database_details(self):
        first = {
            "database": {"name": None, "engine": None},
            "tables": [{"name": "orders", "schema": "dbo"}],
            "types": [{"name": "status", "kind": "enum", "values": ["open"]}],
        }
        second = {
            "database": {"name": "app", "engine": "sqlserver"},
            "tables": [{"name": "customers", "schema": "dbo"}],
            "types": [{"name": "status", "kind": "enum", "values": ["open"]}],
        }
        merged, warnings = merge_schemas([first, second])
        self.assertEqual({"name": "app", "engine": "sqlserver"}, merged["database"])
        self.assertEqual(["orders", "customers"], [table["name"] for table in merged["tables"]])
        self.assertEqual(1, len(merged["types"]))
        self.assertEqual([], warnings)

    def test_validate_schema_accepts_a_types_only_batch_with_no_tables(self):
        types_only = {"database": {"name": None, "engine": None}, "tables": [], "types": [{"name": "x"}]}
        self.assertEqual(types_only, validate_schema(types_only))

    def test_merge_schemas_keeps_the_first_occurrence_of_a_duplicate_table_and_warns(self):
        first_orders = {"name": "orders", "schema": "dbo", "marker": "first"}
        second_orders = {"name": "orders", "schema": "dbo", "marker": "second"}
        first = {"database": {"name": "app", "engine": None}, "tables": [first_orders], "types": []}
        second = {"database": {"name": "app", "engine": None}, "tables": [second_orders], "types": []}

        merged, warnings = merge_schemas([first, second])

        self.assertEqual([first_orders], merged["tables"])
        self.assertEqual(1, len(warnings))
        self.assertIn("more than once", warnings[0]["message"])
        self.assertEqual("DuplicateTable", warnings[0]["errorType"])


if __name__ == "__main__":
    unittest.main()
