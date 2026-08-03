import json
import unittest

from generator import (
    GenerationError,
    generate_from_text,
    load_sources,
    parse_github_blob_url,
    parse_input,
)


API_URL = "https://github.com/example/catalog/blob/main/src/Api/BidsController.cs"
DTO_URL = "https://github.com/example/catalog/blob/main/src/Contracts/BidResponse.cs"


class InputTests(unittest.TestCase):
    def test_accepts_one_discovery_result(self):
        payload = parse_input(
            json.dumps({"apiFile": API_URL, "supportingFiles": [DTO_URL]})
        )
        self.assertEqual(payload["apiFile"], API_URL)
        self.assertEqual(payload["supportingFiles"], [DTO_URL])

    def test_rejects_extra_properties(self):
        with self.assertRaises(GenerationError):
            parse_input(
                json.dumps(
                    {"apiFile": API_URL, "supportingFiles": [], "domain": "catalog"}
                )
            )


class SourceTests(unittest.TestCase):
    def test_parses_github_blob_url(self):
        source = parse_github_blob_url(API_URL)
        self.assertEqual(source.owner, "example")
        self.assertEqual(source.repository, "catalog")
        self.assertEqual(source.ref, "main")
        self.assertEqual(source.path, "src/Api/BidsController.cs")

    def test_rejects_supporting_file_from_another_ref(self):
        with self.assertRaises(GenerationError) as raised:
            load_sources(
                {
                    "apiFile": API_URL,
                    "supportingFiles": [DTO_URL.replace("/main/", "/feature/")],
                },
                fetcher=lambda source: "source",
            )
        self.assertEqual(raised.exception.code, "source_mismatch")


class GenerationTests(unittest.TestCase):
    def test_returns_the_openapi_document_without_a_wrapper(self):
        expected = {
            "openapi": "3.1.0",
            "info": {"title": "Bids API", "version": "1.0.0"},
            "paths": {"/bids": {"get": {"responses": {"200": {"description": "OK"}}}}},
            "components": {"schemas": {}},
        }

        captured_prompt = []
        actual = generate_from_text(
            json.dumps({"apiFile": API_URL, "supportingFiles": [DTO_URL]}),
            fetcher=lambda source: f"source for {source.path}",
            completion=lambda prompt: captured_prompt.append(prompt) or json.dumps(expected),
        )

        self.assertEqual(actual, expected)
        self.assertNotIn("specification", actual)
        self.assertIn("JSON", captured_prompt[0])

    def test_rejects_a_non_openapi_model_response(self):
        with self.assertRaises(GenerationError) as raised:
            generate_from_text(
                json.dumps({"apiFile": API_URL, "supportingFiles": []}),
                fetcher=lambda source: "source",
                completion=lambda prompt: json.dumps({"message": "done"}),
            )
        self.assertEqual(raised.exception.code, "invalid_model_output")


if __name__ == "__main__":
    unittest.main()
