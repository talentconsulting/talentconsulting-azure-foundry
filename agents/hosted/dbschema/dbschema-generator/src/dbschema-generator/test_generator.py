import json
import unittest

from generator import (
    GenerationError,
    _is_database_source,
    _is_ignored,
    generate_from_text,
    parse_input,
    parse_source_url,
    validate_database_schema,
)


SOURCE_URL = "https://github.com/source/catalog/tree/main/src/Data"
SCHEMA = {
    "database": {"name": "catalog", "engine": "PostgreSQL"},
    "tables": [
        {
            "name": "orders",
            "schema": "public",
            "entity": "Order",
            "columns": [
                {
                    "name": "id",
                    "type": "uuid",
                    "nullable": False,
                    "primaryKey": True,
                    "generated": True,
                    "default": "gen_random_uuid()",
                    "ordinal": 1,
                },
                {
                    "name": "customer_id",
                    "type": "uuid",
                    "nullable": False,
                    "primaryKey": False,
                    "generated": False,
                    "default": None,
                    "ordinal": 2,
                },
            ],
            "relationships": [
                {
                    "name": "fk_orders_customers",
                    "type": "many-to-one",
                    "fromColumns": ["customer_id"],
                    "targetTable": "customers",
                    "targetColumns": ["id"],
                    "onDelete": "cascade",
                }
            ],
            "indexes": [
                {
                    "name": "ix_orders_customer_id",
                    "type": "btree",
                    "columns": ["customer_id"],
                    "unique": False,
                    "filter": None,
                }
            ],
        }
    ],
    "types": [{"name": "order_status", "kind": "enum", "values": ["draft", "placed"]}],
}


class InputTests(unittest.TestCase):
    def test_accepts_exact_source_url_contract(self):
        payload = parse_input(json.dumps({"sourceUrl": SOURCE_URL}))
        self.assertEqual(SOURCE_URL, payload["sourceUrl"])
        self.assertEqual("source/catalog", payload["repository"])

    def test_rejects_extra_input_fields(self):
        with self.assertRaises(GenerationError):
            parse_input(json.dumps({"sourceUrl": SOURCE_URL, "extra": True}))

    def test_accepts_a_validated_workflow_source_file_bundle(self):
        file_url = "https://github.com/source/catalog/blob/main/src/Data/Orders.cs"

        payload = parse_input(json.dumps({"sourceUrl": SOURCE_URL, "sourceFiles": [file_url]}))

        self.assertEqual([file_url], payload["sourceFiles"])

    def test_rejects_source_files_from_another_repository(self):
        with self.assertRaises(GenerationError):
            parse_input(json.dumps({
                "sourceUrl": SOURCE_URL,
                "sourceFiles": ["https://github.com/other/catalog/blob/main/src/Data/Orders.cs"],
            }))

    def test_requires_a_github_tree_url(self):
        with self.assertRaises(GenerationError):
            parse_source_url("https://github.com/source/catalog/blob/main/schema.sql")


class DiscoveryTests(unittest.TestCase):
    def test_recognises_database_sources_across_technologies(self):
        self.assertTrue(_is_database_source("src/Data/AppDbContext.cs", "class AppDbContext : DbContext {}"))
        self.assertTrue(_is_database_source("db/schema.sql", "CREATE TABLE orders (id uuid);"))
        self.assertTrue(_is_database_source("prisma/schema.prisma", "model Order { id String @id }"))
        self.assertTrue(_is_database_source("app/order.py", "Order = declarative_base()"))
        self.assertFalse(_is_database_source("src/Api/OrdersController.cs", "class OrdersController {}"))

    def test_ignores_dotted_test_projects(self):
        self.assertTrue(_is_ignored("src/Catalog.UnitTests/Data/FakeContext.cs"))

    def test_ignores_adhoc_maintenance_scripts(self):
        self.assertTrue(
            _is_ignored("src/Catalog.Database/AdhocScripts/Manual/data-backfill.sql")
        )

    def test_ignores_regression_test_directories_and_projects(self):
        self.assertTrue(_is_ignored("src/Database/RegressionTests/OrderRegression.cs"))
        self.assertTrue(_is_ignored("src/Database.RegressionTests/OrderRegression.cs"))


class SchemaTests(unittest.TestCase):
    def test_validates_complete_database_representation(self):
        self.assertEqual(SCHEMA, validate_database_schema(SCHEMA))

    def test_accepts_a_types_only_batch_with_no_tables(self):
        types_only = {"database": {"name": None, "engine": None}, "tables": [], "types": SCHEMA["types"]}
        self.assertEqual(types_only, validate_database_schema(types_only))

    def test_rejects_missing_table_contract_fields(self):
        invalid = json.loads(json.dumps(SCHEMA))
        invalid["tables"][0].pop("indexes")
        with self.assertRaisesRegex(GenerationError, "invalid shape"):
            validate_database_schema(invalid)

    def test_normalises_scalar_column_defaults_to_sql_text(self):
        schema = json.loads(json.dumps(SCHEMA))
        schema["tables"][0]["columns"][0]["default"] = 0
        schema["tables"][0]["columns"][1]["default"] = False

        result = validate_database_schema(schema)

        self.assertEqual("0", result["tables"][0]["columns"][0]["default"])
        self.assertEqual("false", result["tables"][0]["columns"][1]["default"])

    def test_rejects_structured_column_defaults(self):
        schema = json.loads(json.dumps(SCHEMA))
        schema["tables"][0]["columns"][0]["default"] = {"expression": "0"}

        with self.assertRaisesRegex(GenerationError, "string, number, boolean, or null"):
            validate_database_schema(schema)

    def test_generates_schema_from_selected_repository_sources(self):
        prompts = []

        def completion(prompt):
            prompts.append(prompt)
            return json.dumps(SCHEMA)

        result = generate_from_text(
            json.dumps({"sourceUrl": SOURCE_URL}),
            completion=completion,
            source_loader=lambda location: {
                "src/Data/AppDbContext.cs": "public class AppDbContext : DbContext {}",
                "src/Data/Order.cs": "public class Order { public Guid Id { get; set; } }",
            },
        )

        self.assertEqual(SCHEMA, result)
        self.assertIn("AppDbContext.cs", prompts[0])
        self.assertIn("Order.cs", prompts[0])

    def test_rejects_non_json_model_output(self):
        with self.assertRaisesRegex(GenerationError, "valid JSON"):
            generate_from_text(
                json.dumps({"sourceUrl": SOURCE_URL}),
                completion=lambda prompt: "not-json",
                source_loader=lambda location: {"schema.sql": "CREATE TABLE orders(id uuid);"},
            )


if __name__ == "__main__":
    unittest.main()
