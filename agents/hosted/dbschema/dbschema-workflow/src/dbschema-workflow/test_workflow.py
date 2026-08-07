import json
import unittest

from workflow import WorkflowError, parse_workflow_request, run_workflow


SOURCE = "https://github.com/source/app/tree/main/src/Data"
FILE = "https://github.com/source/app/blob/main/src/Data/Orders.cs"
DISCOVERY = {"schemaFiles": [FILE], "excludedFiles": []}
SCHEMA = {
    "database": {"name": "app", "engine": None},
    "tables": [{"name": "orders"}],
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
        self.assertEqual(["discovery", "generator"], calls)
        self.assertEqual(0, result["generatedSchemaCount"])


if __name__ == "__main__":
    unittest.main()
