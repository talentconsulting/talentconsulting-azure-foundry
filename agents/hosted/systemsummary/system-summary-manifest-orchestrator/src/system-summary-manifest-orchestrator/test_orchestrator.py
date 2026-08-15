import json
import unittest

from orchestrator import (
    ManifestError,
    build_generator_input,
    parse_blob_url,
    parse_request,
    run_manifest,
)


MANIFEST_URL = "https://github.com/org/catalogue/blob/main/manifest.json"
BLOB = parse_blob_url(MANIFEST_URL)
APP_ENTRY = {
    "github-repo": "https://github.com/source/app",
    "dbschema": {"path-to-scan": "tree/main/src", "last-commit-hash-scanned": "a" * 40},
    "eventcatalog": {"path-to-scan": "tree/main/src", "last-commit-hash-scanned": "a" * 40},
    "service-dependencies": {"path-to-scan": "tree/main/src", "last-commit-hash-scanned": "a" * 40},
    "specs": {"path-to-scan": "tree/main/src", "last-commit-hash-scanned": "a" * 40},
}
DATABASE = {"database": {"name": "app", "engine": None}, "tables": [{"name": "Orders"}], "types": []}
EVENTS = {"repository": "source/app", "ref": "main", "path": "src", "commands": [], "events": []}
DEPENDENCIES = {"repository": "source/app", "ref": "main", "path": "src", "dependencies": []}
CONTROLLERS = [{"name": "OrdersController.openapi.json"}, {"name": "README.md"}]
SUMMARY = {
    "repository": "source/app",
    "name": "App",
    "description": "Manages orders.",
    "domain": "Orders",
    "capabilities": ["Order management"],
    "confidence": "high",
}


def fetch_fixture(overrides=None):
    urls = {
        "https://raw.githubusercontent.com/org/catalogue/main/manifest.json": [APP_ENTRY],
        "https://raw.githubusercontent.com/org/catalogue/main/app/db-schema/database.schema.json": DATABASE,
        "https://raw.githubusercontent.com/org/catalogue/main/app/event-catalog/events-and-commands.json": EVENTS,
        "https://raw.githubusercontent.com/org/catalogue/main/app/service-dependencies/service-dependencies.json": DEPENDENCIES,
        "https://api.github.com/repos/org/catalogue/contents/app/open-api?ref=main": CONTROLLERS,
    }
    if overrides:
        urls.update(overrides)
    return lambda url: urls.get(url)


class RequestTests(unittest.TestCase):
    def test_requires_source_url(self):
        with self.assertRaises(ManifestError):
            parse_request(json.dumps({}))

    def test_defer_publication_defaults_to_false(self):
        result = parse_request(json.dumps({"sourceUrl": MANIFEST_URL}))
        self.assertFalse(result["deferPublication"])

    def test_rejects_unsupported_fields(self):
        with self.assertRaises(ManifestError):
            parse_request(json.dumps({"sourceUrl": MANIFEST_URL, "extra": True}))


class BuildGeneratorInputTests(unittest.TestCase):
    def test_fetches_every_declared_catalog_and_lists_controllers(self):
        result = build_generator_input(APP_ENTRY, BLOB, fetch_fixture())
        self.assertEqual("source/app", result["repository"])
        self.assertEqual(DATABASE, result["database"])
        self.assertEqual(EVENTS, result["events"])
        self.assertEqual(DEPENDENCIES, result["dependencies"])
        self.assertEqual(["OrdersController"], result["apiControllers"])

    def test_skips_catalogs_the_manifest_does_not_declare(self):
        sparse_entry = {"github-repo": "https://github.com/source/app"}
        result = build_generator_input(sparse_entry, BLOB, fetch_fixture())
        self.assertIsNone(result["database"])
        self.assertIsNone(result["events"])
        self.assertIsNone(result["dependencies"])
        self.assertEqual([], result["apiControllers"])

    def test_treats_a_missing_declared_file_as_null(self):
        fetch = fetch_fixture({"https://raw.githubusercontent.com/org/catalogue/main/app/db-schema/database.schema.json": None})
        result = build_generator_input(APP_ENTRY, BLOB, fetch)
        self.assertIsNone(result["database"])

    def test_rejects_an_entry_without_a_repository(self):
        with self.assertRaises(ManifestError):
            build_generator_input({}, BLOB, fetch_fixture())


class RunManifestTests(unittest.TestCase):
    def test_generates_and_publishes_once(self):
        calls = []

        def invoke(project, name, model, payload, max_attempts=2):
            calls.append(name)
            if name == "generator":
                self.assertEqual("source/app", payload["repository"])
                return SUMMARY
            self.assertEqual("publisher", name)
            self.assertEqual("system-summaries.json", payload["targetPath"])
            self.assertEqual([SUMMARY], payload["fileContent"]["systems"])
            return {"success": True, "status": "created", "pullRequestUrl": "https://github.com/org/catalogue/pull/1"}

        result = run_manifest(
            object(), {"sourceUrl": MANIFEST_URL, "deferPublication": False},
            "generator", "publisher", "gpt-4o", fetch=fetch_fixture(), invoker=invoke,
        )

        self.assertTrue(result["success"])
        self.assertEqual(1, result["generatedSystemCount"])
        self.assertEqual(["generator", "publisher"], calls)

    def test_deferred_run_skips_publication(self):
        def invoke(project, name, model, payload, max_attempts=2):
            self.assertEqual("generator", name)
            return SUMMARY

        result = run_manifest(
            object(), {"sourceUrl": MANIFEST_URL, "deferPublication": True},
            "generator", "publisher", "gpt-4o", fetch=fetch_fixture(), invoker=invoke,
        )

        self.assertTrue(result["success"])
        self.assertIsNone(result["pullRequest"])
        self.assertEqual([SUMMARY], result["systems"])

    def test_a_failing_repository_does_not_block_others(self):
        second_entry = {**APP_ENTRY, "github-repo": "https://github.com/source/billing"}
        fetch = fetch_fixture(
            {"https://raw.githubusercontent.com/org/catalogue/main/manifest.json": [APP_ENTRY, second_entry]}
        )

        def invoke(project, name, model, payload, max_attempts=2):
            if name != "generator":
                raise AssertionError("Publisher must not be called when a repository failed.")
            if payload["repository"] == "source/billing":
                return {"error": {"code": "invalid_model_output", "message": "bad summary"}}
            return SUMMARY

        result = run_manifest(
            object(), {"sourceUrl": MANIFEST_URL, "deferPublication": True},
            "generator", "publisher", "gpt-4o", fetch=fetch, invoker=invoke,
        )

        self.assertTrue(result["success"] is False)
        self.assertEqual(1, result["generatedSystemCount"])
        self.assertEqual(1, len(result["failures"]))
        self.assertEqual("source/billing", result["failures"][0]["repository"])

    def test_every_repository_failing_returns_no_systems(self):
        def invoke(project, name, model, payload, max_attempts=2):
            return {"error": {"code": "invalid_model_output", "message": "bad summary"}}

        result = run_manifest(
            object(), {"sourceUrl": MANIFEST_URL, "deferPublication": True},
            "generator", "publisher", "gpt-4o", fetch=fetch_fixture(), invoker=invoke,
        )

        self.assertFalse(result["success"])
        self.assertEqual(0, result["generatedSystemCount"])
        self.assertEqual([], result["systems"])


if __name__ == "__main__":
    unittest.main()
