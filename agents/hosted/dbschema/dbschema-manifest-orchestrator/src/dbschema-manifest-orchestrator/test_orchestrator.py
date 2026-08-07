import json
import unittest

from orchestrator import ManifestError, parse_blob_url, parse_request, run_manifest, validate_manifest


MANIFEST_URL = "https://github.com/target/schemas/blob/main/repoManifest.json"
REPO_URL = "https://github.com/source/app"
OLD_SHA = "1" * 40
NEW_SHA = "2" * 40
SCHEMA = {
    "database": {"name": "app", "engine": None},
    "tables": [{"name": "orders"}],
    "types": [],
}


def manifest(last_commit=OLD_SHA):
    return [
        {
            "github-repo": REPO_URL,
            "dbschema": {
                "path-to-scan": "tree/main/src/Data",
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
        self.assertEqual("https://github.com/source/app/tree/main/src/Data", entry.source_url)

    def test_shared_manifest_ignores_specs_and_entries_without_dbschema(self):
        shared = manifest("")
        shared[0]["specs"] = {
            "path-to-scan": "tree/main/src/Api",
            "last-commit-hash-scanned": OLD_SHA,
        }
        shared.append(
            {
                "specs": {
                    "path-to-scan": "tree/main/src/Api",
                    "last-commit-hash-scanned": OLD_SHA,
                },
                "owner": "api-platform",
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
                self.assertEqual(
                    {"sourceUrl": "https://github.com/source/app/tree/main/src/Data", "deferPublication": True},
                    payload,
                )
                return {
                    "success": True,
                    "schemas": [{"sourceUrl": payload["sourceUrl"], "schema": SCHEMA}],
                }
            if name == "publisher":
                self.assertEqual(1, max_attempts)
                self.assertEqual(
                    NEW_SHA,
                    payload["manifestFile"]["content"][0]["dbschema"]["last-commit-hash-scanned"],
                )
                self.assertEqual(
                    "app/db-schema/database.schema.json",
                    payload["schemas"][0]["targetPath"],
                )
                self.assertEqual(
                    "https://github.com/source/app/tree/main/src/Data",
                    payload["schemas"][0]["sourceUrl"],
                )
                return {
                    "success": True,
                    "status": "created",
                    "pullRequestUrl": "https://github.com/target/schemas/pull/1",
                }
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
        self.assertEqual(1, result["generatedSchemaCount"])
        self.assertEqual(["workflow", "publisher"], [call[0] for call in calls])

    def test_calls_workflow_once_for_every_changed_dbschema_repository(self):
        second = manifest()
        second[0]["github-repo"] = "https://github.com/source/accounts"
        calls = []

        def invoke(project, name, model, payload, max_attempts=2):
            calls.append(name)
            if name == "workflow":
                return {
                    "success": True,
                    "schemas": [{"sourceUrl": payload["sourceUrl"], "schema": SCHEMA}],
                }
            return {"success": True, "status": "created"}

        result = run_manifest(
            object(),
            {"sourceUrl": MANIFEST_URL},
            "workflow",
            "publisher",
            "gpt-4o",
            manifest_loader=lambda blob: manifest() + second,
            commit_resolver=lambda entry: NEW_SHA,
            invoker=invoke,
        )

        self.assertTrue(result["success"])
        self.assertEqual(2, result["generatedRepositoryCount"])
        self.assertEqual(2, result["generatedSchemaCount"])
        self.assertEqual(["workflow", "workflow", "publisher"], calls)

    def test_legacy_db_schema_node_remains_supported(self):
        legacy = manifest("")
        legacy[0]["db-schema"] = legacy[0].pop("dbschema")

        entry = validate_manifest(legacy, 25)[0]

        self.assertEqual("db-schema", entry.manifest_node)

    def test_rejects_ambiguous_dbschema_node_aliases(self):
        ambiguous = manifest("")
        ambiguous[0]["db-schema"] = dict(ambiguous[0]["dbschema"])

        with self.assertRaisesRegex(ManifestError, "both dbschema and db-schema"):
            validate_manifest(ambiguous, 25)

    def test_generation_failure_does_not_update_or_publish(self):
        def invoke(project, name, model, payload, max_attempts=2):
            return {
                "success": False,
                "generationErrors": [{"message": "No database sources found."}],
                "schemas": [],
            }

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
        self.assertEqual("schema_workflow", result["failures"][0]["stage"])
        self.assertIsNone(result["pullRequest"])


if __name__ == "__main__":
    unittest.main()
