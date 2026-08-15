import json
import unittest

from generator import GenerationError, SourceLocation, generate_from_text, parse_input, source_prompt, validate_catalog


SOURCE = "https://github.com/source/app/tree/main/src"
FILES = ["https://github.com/source/app/blob/main/src/Program.cs"]
DRAWIO = '<mxfile><diagram name="Context"><mxGraphModel><root /></mxGraphModel></diagram></mxfile>'
CATALOG = {
    "repository": "source/app",
    "ref": "main",
    "path": "src",
    "c4Model": {
        "systemName": "Application",
        "description": "Application under analysis.",
        "people": [{"id": "user", "name": "User", "description": "Uses the application.", "evidence": [{"sourceFile": "src/Program.cs", "reason": "HTTP entrypoint."}]}],
        "systems": [{"id": "application", "name": "Application", "description": "System under analysis.", "external": False, "evidence": [{"sourceFile": "src/Program.cs", "reason": "Application startup."}]}],
        "containers": [{"id": "web-api", "parentSystemId": "application", "name": "Web API", "technology": ".NET", "description": "Handles HTTP requests.", "evidence": [{"sourceFile": "src/Program.cs", "reason": "WebApplication startup."}]}],
        "relationships": [{"sourceId": "user", "targetId": "application", "description": "Uses", "technology": "HTTPS", "evidence": [{"sourceFile": "src/Program.cs", "reason": "HTTP entrypoint."}]}],
        "evidence": [{"sourceFile": "src/Program.cs", "reason": "Selected source bundle."}],
    },
    "diagrams": {
        "context": {"format": "drawio", "filename": "context.drawio", "drawioXml": DRAWIO},
        "container": {"format": "drawio", "filename": "container.drawio", "drawioXml": DRAWIO},
    },
}


class GeneratorTests(unittest.TestCase):
    def test_input_requires_selected_same_repository_files(self):
        self.assertEqual(FILES, parse_input(json.dumps({"sourceUrl": SOURCE, "sourceFiles": FILES}))["sourceFiles"])
        with self.assertRaises(GenerationError):
            parse_input(json.dumps({"sourceUrl": SOURCE}))
        with self.assertRaises(GenerationError):
            parse_input(json.dumps({"sourceUrl": SOURCE, "sourceFiles": ["https://github.com/other/app/blob/main/X.cs"]}))

    def test_source_prompt_requests_c4_json(self):
        prompt = source_prompt(SourceLocation("source", "app", "main", "src"), {"src/Program.cs": "WebApplication.CreateBuilder(args);"})
        self.assertIn("C4", prompt)
        self.assertIn("JSON", prompt)

    def test_validates_catalog_contract_evidence_and_drawio(self):
        result = validate_catalog(json.loads(json.dumps(CATALOG)), SourceLocation("source", "app", "main", "src"), {"src/Program.cs"})
        self.assertEqual("Application", result["c4Model"]["systemName"])
        bad = json.loads(json.dumps(CATALOG))
        bad["c4Model"]["systems"][0]["evidence"][0]["sourceFile"] = "src/NotSupplied.cs"
        with self.assertRaisesRegex(GenerationError, "supplied source"):
            validate_catalog(bad, source_paths={"src/Program.cs"})
        bad = json.loads(json.dumps(CATALOG))
        bad["diagrams"]["context"]["drawioXml"] = "<not-xml"
        with self.assertRaisesRegex(GenerationError, "draw.io XML"):
            validate_catalog(bad, source_paths={"src/Program.cs"})

    def test_rejects_unknown_relationship_targets(self):
        bad = json.loads(json.dumps(CATALOG))
        bad["c4Model"]["relationships"][0]["targetId"] = "missing"
        with self.assertRaisesRegex(GenerationError, "unknown element"):
            validate_catalog(bad, source_paths={"src/Program.cs"})

    def test_generate_downloads_only_selected_files(self):
        loaded = []

        def load(location, files):
            loaded.extend(files)
            return {"src/Program.cs": "WebApplication.CreateBuilder(args);"}

        result = generate_from_text(
            json.dumps({"sourceUrl": SOURCE, "sourceFiles": FILES}),
            completion=lambda prompt: json.dumps(CATALOG),
            source_loader=load,
        )
        self.assertEqual(FILES, loaded)
        self.assertEqual("context.drawio", result["diagrams"]["context"]["filename"])


if __name__ == "__main__":
    unittest.main()
