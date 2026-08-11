import json
import unittest

from generator import GenerationError, SourceLocation, generate_from_text, parse_input, source_prompt, validate_catalog


SOURCE = "https://github.com/source/app/tree/main/src/Application"
FILES = ["https://github.com/source/app/blob/main/src/Application/Commands/CreateOrderCommand.cs"]
CATALOG = {
    "repository": "source/app",
    "ref": "main",
    "path": "src/Application",
    "commands": [
        {
            "name": "CreateOrderCommand",
            "namespace": "App.Commands",
            "sourceFile": "src/Application/Commands/CreateOrderCommand.cs",
            "description": None,
            "fields": [{"name": "orderId", "type": "Guid", "required": True, "description": None}],
            "handlers": [{"name": "CreateOrderHandler", "sourceFile": "src/Application/Handlers/CreateOrderHandler.cs"}],
        }
    ],
    "events": [],
}


class GeneratorTests(unittest.TestCase):
    def test_source_prompt_explicitly_requests_json_for_json_object_mode(self):
        prompt = source_prompt(
            SourceLocation("source", "app", "main", "src/Application"),
            {"src/Application/Commands/CreateOrderCommand.cs": "record CreateOrderCommand();"},
        )

        self.assertIn("JSON", prompt)

    def test_input_requires_selected_same_repository_files(self):
        payload = parse_input(json.dumps({"sourceUrl": SOURCE, "sourceFiles": FILES}))
        self.assertEqual(FILES, payload["sourceFiles"])
        with self.assertRaises(GenerationError):
            parse_input(json.dumps({"sourceUrl": SOURCE}))
        with self.assertRaises(GenerationError):
            parse_input(json.dumps({"sourceUrl": SOURCE, "sourceFiles": ["https://github.com/other/app/blob/main/X.cs"]}))

    def test_validates_catalog_contract(self):
        location = SourceLocation("source", "app", "main", "src/Application")
        self.assertEqual(CATALOG, validate_catalog(json.loads(json.dumps(CATALOG)), location))

    def test_rejects_invented_source_identity_and_bad_fields(self):
        wrong = json.loads(json.dumps(CATALOG))
        wrong["repository"] = "other/app"
        with self.assertRaisesRegex(GenerationError, "identity"):
            validate_catalog(wrong, SourceLocation("source", "app", "main", "src/Application"))
        malformed = json.loads(json.dumps(CATALOG))
        malformed["commands"][0]["fields"][0]["required"] = "yes"
        with self.assertRaisesRegex(GenerationError, "boolean"):
            validate_catalog(malformed)

    def test_generate_downloads_only_selected_files_and_validates_output(self):
        loaded = []

        def load(location, files):
            loaded.extend(files)
            return {"src/Application/Commands/CreateOrderCommand.cs": "record CreateOrderCommand(Guid orderId);"}

        result = generate_from_text(
            json.dumps({"sourceUrl": SOURCE, "sourceFiles": FILES}),
            completion=lambda prompt: json.dumps(CATALOG),
            source_loader=load,
        )

        self.assertEqual(FILES, loaded)
        self.assertEqual("CreateOrderCommand", result["commands"][0]["name"])

    def test_sorts_messages_deterministically(self):
        catalog = json.loads(json.dumps(CATALOG))
        second = json.loads(json.dumps(catalog["commands"][0]))
        second["name"] = "ApproveOrderCommand"
        catalog["commands"].append(second)
        result = validate_catalog(catalog)
        self.assertEqual(["ApproveOrderCommand", "CreateOrderCommand"], [item["name"] for item in result["commands"]])


if __name__ == "__main__":
    unittest.main()
