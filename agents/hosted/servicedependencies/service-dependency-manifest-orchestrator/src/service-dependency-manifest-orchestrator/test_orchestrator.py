import json
import threading
import unittest
import urllib.error
from io import BytesIO
from unittest.mock import patch

from orchestrator import ManifestEntry, ManifestError, _read_url, latest_commit, parse_request, run_manifest, validate_manifest


MANIFEST_URL = "https://github.com/target/catalogs/blob/main/manifest.json"
OLD_SHA = "1" * 40
NEW_SHA = "2" * 40
CATALOG = {
    "repository": "source/app", "ref": "main", "path": "src", "systemName": "App",
    "containers": [{"id": "app", "name": "App", "type": "api", "evidence": []}],
    "dependencies": [{"sourceId": "app", "name": "Accounts API"}],
}


def manifest(last_commit=OLD_SHA):
    return [{
        "github-repo": "https://github.com/source/app",
        "specs": {"path-to-scan": "tree/main/src/Api", "last-commit-hash-scanned": OLD_SHA},
        "service-dependencies": {"path-to-scan": "tree/main/src", "last-commit-hash-scanned": last_commit},
    }]


class ManifestTests(unittest.TestCase):
    def test_github_error_includes_api_message(self):
        error = urllib.error.HTTPError(
            "https://api.github.com/repos/source/app/commits/main",
            422,
            "Unprocessable Content",
            {},
            BytesIO(b'{"message":"No commit found for SHA: main"}'),
        )
        with patch("urllib.request.urlopen", side_effect=error):
            with self.assertRaisesRegex(ManifestError, "No commit found for SHA: main"):
                _read_url(error.url)

    def test_latest_commit_rejects_a_ref_that_is_not_the_default_branch(self):
        entry = ManifestEntry(
            index=0, owner="source", repository="app", repository_url="https://github.com/source/app",
            ref="feature-x", scan_path="src", path_to_scan="tree/feature-x/src", last_commit="",
        )

        def fake_read_url(url):
            if url == "https://api.github.com/repos/source/app":
                return json.dumps({"default_branch": "main"}).encode("utf-8")
            raise AssertionError(f"unexpected URL {url}")

        with patch("orchestrator._read_url", side_effect=fake_read_url):
            with self.assertRaisesRegex(ManifestError, "default branch is 'main'"):
                latest_commit(entry)

    def test_latest_commit_resolves_the_sha_for_the_default_branch(self):
        entry = ManifestEntry(
            index=0, owner="source", repository="app", repository_url="https://github.com/source/app",
            ref="main", scan_path="src", path_to_scan="tree/main/src", last_commit="",
        )

        def fake_read_url(url):
            if url == "https://api.github.com/repos/source/app":
                return json.dumps({"default_branch": "main"}).encode("utf-8")
            if url == "https://api.github.com/repos/source/app/commits/main":
                return json.dumps({"sha": NEW_SHA}).encode("utf-8")
            raise AssertionError(f"unexpected URL {url}")

        with patch("orchestrator._read_url", side_effect=fake_read_url):
            self.assertEqual(NEW_SHA, latest_commit(entry))

    def test_input_has_exactly_source_url(self):
        self.assertEqual(MANIFEST_URL, parse_request(json.dumps({"sourceUrl": MANIFEST_URL}))["sourceUrl"])
        with self.assertRaises(ManifestError):
            parse_request(json.dumps({"sourceUrl": MANIFEST_URL, "extra": True}))

    def test_shared_manifest_selects_only_service_dependencies(self):
        shared = manifest("")
        shared.append({
            "github-repo": "https://github.com/source/other",
            "eventcatalog": {"path-to-scan": "tree/main/src", "last-commit-hash-scanned": ""},
        })
        entries = validate_manifest(shared, 25)
        self.assertEqual(1, len(entries))
        self.assertEqual("source/app", entries[0].repository_name)

    def test_up_to_date_manifest_does_not_invoke_agents(self):
        result = run_manifest(
            object(), {"sourceUrl": MANIFEST_URL}, "workflow", "publisher", "gpt-4o",
            manifest_loader=lambda blob: manifest(NEW_SHA), commit_resolver=lambda entry: NEW_SHA,
            invoker=lambda *args, **kwargs: self.fail("No agent should be invoked."),
        )
        self.assertTrue(result["success"])
        self.assertEqual("up_to_date", result["status"])

    def test_changed_repository_generates_and_publishes_atomically(self):
        calls = []

        def invoke(project, name, model, payload, max_attempts=2):
            calls.append((name, payload))
            if name == "workflow":
                return {"success": True, "catalogs": [{"sourceUrl": payload["sourceUrl"], "catalog": CATALOG}]}
            self.assertEqual(NEW_SHA, payload["manifestFile"]["content"][0]["service-dependencies"]["last-commit-hash-scanned"])
            self.assertEqual("app/service-dependencies/service-dependencies.json", payload["catalogs"][0]["targetPath"])
            return {"success": True, "status": "created"}

        result = run_manifest(
            object(), {"sourceUrl": MANIFEST_URL}, "workflow", "publisher", "gpt-4o",
            manifest_loader=lambda blob: manifest(), commit_resolver=lambda entry: NEW_SHA, invoker=invoke,
        )
        self.assertTrue(result["success"])
        self.assertEqual(["workflow", "publisher"], [call[0] for call in calls])

    def test_puml_diagram_passes_through_to_the_publisher_when_present(self):
        def invoke(project, name, model, payload, max_attempts=2):
            if name == "workflow":
                return {
                    "success": True,
                    "catalogs": [{"sourceUrl": payload["sourceUrl"], "catalog": CATALOG, "puml": "@startuml\n@enduml\n"}],
                }
            self.assertEqual("@startuml\n@enduml\n", payload["catalogs"][0]["puml"])
            return {"success": True, "status": "created"}

        result = run_manifest(
            object(), {"sourceUrl": MANIFEST_URL}, "workflow", "publisher", "gpt-4o",
            manifest_loader=lambda blob: manifest(), commit_resolver=lambda entry: NEW_SHA, invoker=invoke,
        )
        self.assertTrue(result["success"])

    def test_missing_puml_is_tolerated_for_backward_compatibility(self):
        def invoke(project, name, model, payload, max_attempts=2):
            if name == "workflow":
                return {"success": True, "catalogs": [{"sourceUrl": payload["sourceUrl"], "catalog": CATALOG}]}
            self.assertNotIn("puml", payload["catalogs"][0])
            return {"success": True, "status": "created"}

        result = run_manifest(
            object(), {"sourceUrl": MANIFEST_URL}, "workflow", "publisher", "gpt-4o",
            manifest_loader=lambda blob: manifest(), commit_resolver=lambda entry: NEW_SHA, invoker=invoke,
        )
        self.assertTrue(result["success"])

    def test_repositories_are_generated_concurrently(self):
        two_repo_manifest = manifest() + [{
            "github-repo": "https://github.com/source/other",
            "service-dependencies": {"path-to-scan": "tree/main/src", "last-commit-hash-scanned": ""},
        }]
        barrier = threading.Barrier(2, timeout=5)

        def invoke(project, name, model, payload, max_attempts=2):
            if name != "workflow":
                return {"success": True, "status": "created"}
            # Only releases once both repositories' workflow calls have reached this point at the
            # same time -- if they ran one at a time, this would time out and break the barrier.
            barrier.wait()
            repository = "/".join(payload["sourceUrl"].split("/")[3:5])
            catalog = json.loads(json.dumps(CATALOG))
            catalog["repository"] = repository
            return {"success": True, "catalogs": [{"sourceUrl": payload["sourceUrl"], "catalog": catalog}]}

        result = run_manifest(
            object(), {"sourceUrl": MANIFEST_URL}, "workflow", "publisher", "gpt-4o",
            manifest_loader=lambda blob: two_repo_manifest, commit_resolver=lambda entry: NEW_SHA, invoker=invoke,
        )
        self.assertTrue(result["success"])
        self.assertEqual(2, result["generatedRepositoryCount"])

    def test_generation_failure_does_not_update_or_publish(self):
        def invoke(project, name, model, payload, max_attempts=2):
            return {"success": False, "generationErrors": [{"message": "No dependencies found."}], "catalogs": []}

        result = run_manifest(
            object(), {"sourceUrl": MANIFEST_URL}, "workflow", "publisher", "gpt-4o",
            manifest_loader=lambda blob: manifest(), commit_resolver=lambda entry: NEW_SHA, invoker=invoke,
        )
        self.assertFalse(result["success"])
        self.assertEqual("catalog_workflow", result["failures"][0]["stage"])
        self.assertIsNone(result["pullRequest"])


if __name__ == "__main__":
    unittest.main()
