import json
import unittest

from orchestrator import ManifestError, parse_blob_url, parse_request, run_manifest, validate_manifest


MANIFEST_URL = "https://github.com/target/specs/blob/main/repoManifest.json"
REPO_URL = "https://github.com/source/app"
OLD_SHA = "1" * 40
NEW_SHA = "2" * 40
API_FILE = "https://github.com/source/app/blob/main/src/Api/BidsController.cs"
SPEC = {
    "openapi": "3.1.0",
    "info": {"title": "API", "version": "1.0.0"},
    "paths": {"/bids": {}},
    "components": {"schemas": {}},
}


def manifest(last_commit=OLD_SHA):
    return [
        {
            "github-repo": REPO_URL,
            "specs": {
                "path-to-scan": "tree/main/src/Api",
                "last-commit-hash-scanned": last_commit,
            },
        }
    ]


class ManifestTests(unittest.TestCase):
    def test_input_has_exactly_source_url(self):
        self.assertEqual(MANIFEST_URL, parse_request(json.dumps({"sourceUrl": MANIFEST_URL}))["sourceUrl"])
        with self.assertRaises(ManifestError):
            parse_request(json.dumps({"sourceUrl": MANIFEST_URL, "extra": True}))

    def test_validates_manifest_schema(self):
        entry = validate_manifest(manifest(""), 25)[0]
        self.assertEqual("source/app", entry.repository_name)
        self.assertEqual("main", entry.ref)
        self.assertEqual("https://github.com/source/app/tree/main/src/Api", entry.source_url)

    def test_shared_manifest_ignores_db_schema_and_entries_without_specs(self):
        shared = manifest("")
        shared[0]["db-schema"] = {
            "path-to-scan": "tree/main/src/Data",
            "last-commit-hash-scanned": "",
        }
        shared.append(
            {
                "dbschema": {
                    "path-to-scan": "tree/main/src/Data",
                    "last-commit-hash-scanned": "",
                },
                "owner": "data-platform",
            }
        )

        entries = validate_manifest(shared, 25)

        self.assertEqual(1, len(entries))
        self.assertEqual("source/app", entries[0].repository_name)

    def test_rejects_duplicate_repositories(self):
        with self.assertRaisesRegex(ManifestError, "duplicated"):
            validate_manifest(manifest() + manifest(), 25)

    def test_up_to_date_manifest_does_not_invoke_agents(self):
        def fail_invoker(*args, **kwargs):
            raise AssertionError("No agent should be invoked.")

        result = run_manifest(
            object(),
            {"sourceUrl": MANIFEST_URL},
            "workflow",
            "publisher",
            "gpt-4o",
            manifest_loader=lambda blob: manifest(NEW_SHA),
            commit_resolver=lambda entry: NEW_SHA,
            invoker=fail_invoker,
        )
        self.assertTrue(result["success"])
        self.assertEqual("up_to_date", result["status"])
        self.assertIsNone(result["pullRequest"])

    def test_changed_repository_generates_then_publishes_manifest_atomically(self):
        calls = []

        def invoke(project, name, model, payload, max_attempts=2):
            calls.append((name, payload, max_attempts))
            if name == "workflow":
                self.assertTrue(payload["deferPublication"])
                return {
                    "success": True,
                    "specifications": [{"apiFile": API_FILE, "specification": SPEC}],
                }
            if name == "publisher":
                self.assertEqual(1, max_attempts)
                self.assertEqual(NEW_SHA, payload["manifestFile"]["content"][0]["specs"]["last-commit-hash-scanned"])
                self.assertEqual(
                    "app/open-api/BidsController.openapi.json",
                    payload["specifications"][0]["targetPath"],
                )
                return {"success": True, "status": "created", "pullRequestUrl": "https://github.com/target/specs/pull/1"}
            raise AssertionError(name)

        result = run_manifest(
            object(),
            {"sourceUrl": MANIFEST_URL},
            "workflow",
            "publisher",
            "gpt-4o",
            manifest_loader=lambda blob: manifest(),
            commit_resolver=lambda entry: NEW_SHA,
            invoker=invoke,
        )
        self.assertTrue(result["success"])
        self.assertEqual(1, result["generatedRepositoryCount"])
        self.assertEqual(["workflow", "publisher"], [call[0] for call in calls])

    def test_generation_failure_does_not_update_or_publish(self):
        def invoke(project, name, model, payload, max_attempts=2):
            return {"success": False, "generationErrors": [{"apiFile": API_FILE}]}

        result = run_manifest(
            object(),
            {"sourceUrl": MANIFEST_URL},
            "workflow",
            "publisher",
            "gpt-4o",
            manifest_loader=lambda blob: manifest(),
            commit_resolver=lambda entry: NEW_SHA,
            invoker=invoke,
        )
        self.assertFalse(result["success"])
        self.assertEqual("spec_generation", result["failures"][0]["stage"])
        self.assertIsNone(result["pullRequest"])


if __name__ == "__main__":
    unittest.main()
