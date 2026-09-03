import json
import unittest
from unittest.mock import patch

from orchestrator import (
    ManifestEntry,
    ManifestError,
    MANIFEST_NODE,
    latest_commit,
    parse_request,
    run_manifest,
    validate_manifest,
)


MANIFEST_URL = "https://github.com/target/catalogs/blob/main/manifest.json"
OLD_SHA = "1" * 40
NEW_SHA = "2" * 40
OTHER_NEW_SHA = "3" * 40


def make_catalog(repository="source/app", ref="main", path="src", local_services=None, configuration_keys=None):
    return {
        "repository": repository,
        "ref": ref,
        "path": path,
        "localServices": local_services if local_services is not None else [{"name": "postgres", "kind": "database"}],
        "configurationKeys": configuration_keys if configuration_keys is not None else ["DATABASE_URL"],
    }


def manifest(last_commit=OLD_SHA, extra_entries=None):
    entries = [{
        "github-repo": "https://github.com/source/app",
        "local-dev-config": {"path-to-scan": "tree/main/src", "last-commit-hash-scanned": last_commit},
    }]
    if extra_entries:
        entries.extend(extra_entries)
    return entries


class ManifestTests(unittest.TestCase):
    def test_validate_manifest_skips_entries_without_local_dev_config_node(self):
        shared = manifest("")
        shared.append({
            "github-repo": "https://github.com/source/other",
            "c4": {"path-to-scan": "tree/main/src", "last-commit-hash-scanned": ""},
        })
        entries = validate_manifest(shared, 25)
        self.assertEqual(1, len(entries))
        self.assertEqual("source/app", entries[0].repository_name)

    def test_validate_manifest_rejects_invalid_commit_hash_or_path_to_scan(self):
        bad_commit = manifest("not-a-sha")
        with self.assertRaises(ManifestError):
            validate_manifest(bad_commit, 25)

        bad_path = manifest("")
        bad_path[0][MANIFEST_NODE]["path-to-scan"] = "src"
        with self.assertRaises(ManifestError):
            validate_manifest(bad_path, 25)

    def test_validate_manifest_rejects_duplicate_repositories(self):
        duplicated = manifest("")
        duplicated.append({
            "github-repo": "https://github.com/source/app",
            "local-dev-config": {"path-to-scan": "tree/main/other", "last-commit-hash-scanned": ""},
        })
        with self.assertRaises(ManifestError):
            validate_manifest(duplicated, 25)

    def test_latest_commit_rejects_ref_not_matching_default_branch(self):
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

    def test_input_has_exactly_source_url(self):
        self.assertEqual(MANIFEST_URL, parse_request(json.dumps({"sourceUrl": MANIFEST_URL}))["sourceUrl"])
        with self.assertRaises(ManifestError):
            parse_request(json.dumps({"sourceUrl": MANIFEST_URL, "extra": True}))

    def test_run_manifest_returns_up_to_date_without_invoking_any_agent(self):
        result = run_manifest(
            object(), {"sourceUrl": MANIFEST_URL}, "workflow", "publisher", "gpt-4o",
            manifest_loader=lambda blob: manifest(NEW_SHA), commit_resolver=lambda entry: NEW_SHA,
            invoker=lambda *args, **kwargs: self.fail("No agent should be invoked."),
        )
        self.assertTrue(result["success"])
        self.assertEqual("up_to_date", result["status"])
        self.assertEqual(0, result["changedCount"])
        self.assertIsNone(result["pullRequest"])

    def test_run_manifest_calls_workflow_once_per_changed_repo_with_defer_publication_true(self):
        calls = []

        def invoke(project, name, model, payload, max_attempts=2):
            calls.append((name, payload))
            if name == "workflow":
                return {"success": True, "catalogs": [{"sourceUrl": payload["sourceUrl"], "catalog": make_catalog()}]}
            return {"success": True, "status": "created"}

        result = run_manifest(
            object(), {"sourceUrl": MANIFEST_URL}, "workflow", "publisher", "gpt-4o",
            manifest_loader=lambda blob: manifest(), commit_resolver=lambda entry: NEW_SHA, invoker=invoke,
        )
        self.assertTrue(result["success"])
        workflow_calls = [call for call in calls if call[0] == "workflow"]
        self.assertEqual(1, len(workflow_calls))
        self.assertEqual(
            {"sourceUrl": "https://github.com/source/app/tree/main/src", "deferPublication": True},
            workflow_calls[0][1],
        )

    def test_run_manifest_allows_workflow_result_with_empty_local_services(self):
        def invoke(project, name, model, payload, max_attempts=2):
            if name == "workflow":
                empty_catalog = make_catalog(local_services=[], configuration_keys=[])
                return {"success": True, "catalogs": [{"sourceUrl": payload["sourceUrl"], "catalog": empty_catalog}]}
            self.assertEqual(1, len(payload["catalogs"]))
            return {"success": True, "status": "created"}

        result = run_manifest(
            object(), {"sourceUrl": MANIFEST_URL}, "workflow", "publisher", "gpt-4o",
            manifest_loader=lambda blob: manifest(), commit_resolver=lambda entry: NEW_SHA, invoker=invoke,
        )
        self.assertTrue(result["success"])
        self.assertEqual(1, result["generatedCatalogCount"])
        self.assertEqual([], result["failures"])

    def test_run_manifest_updates_commit_hash_only_on_success(self):
        two_repo_manifest = manifest(OLD_SHA, extra_entries=[{
            "github-repo": "https://github.com/source/other",
            "local-dev-config": {"path-to-scan": "tree/main/src", "last-commit-hash-scanned": OLD_SHA},
        }])

        def commit_resolver(entry):
            return NEW_SHA if entry.repository == "app" else OTHER_NEW_SHA

        published = {}

        def invoke(project, name, model, payload, max_attempts=2):
            if name == "workflow":
                if payload["sourceUrl"].endswith("source/app/tree/main/src"):
                    return {"success": True, "catalogs": [{"sourceUrl": payload["sourceUrl"], "catalog": make_catalog()}]}
                return {"success": False, "generationErrors": [{"message": "Could not scan repository."}], "catalogs": []}
            published.update(payload)
            return {"success": True, "status": "created"}

        result = run_manifest(
            object(), {"sourceUrl": MANIFEST_URL}, "workflow", "publisher", "gpt-4o",
            manifest_loader=lambda blob: two_repo_manifest, commit_resolver=commit_resolver, invoker=invoke,
        )
        # One of the two repositories failed, so the overall run is not fully successful even
        # though a pull request was published for the repository that did succeed.
        self.assertFalse(result["success"])
        self.assertIsNotNone(result["pullRequest"])
        manifest_sent = published["manifestFile"]["content"]
        self.assertEqual(NEW_SHA, manifest_sent[0][MANIFEST_NODE]["last-commit-hash-scanned"])
        self.assertEqual(OLD_SHA, manifest_sent[1][MANIFEST_NODE]["last-commit-hash-scanned"])
        self.assertEqual(1, len(result["failures"]))
        self.assertEqual("workflow", result["failures"][0]["stage"])

    def test_run_manifest_combines_all_successful_catalogs_into_one_pr_creator_call(self):
        two_repo_manifest = manifest(OLD_SHA, extra_entries=[{
            "github-repo": "https://github.com/source/other",
            "local-dev-config": {"path-to-scan": "tree/main/src", "last-commit-hash-scanned": OLD_SHA},
        }])
        publisher_calls = []

        def invoke(project, name, model, payload, max_attempts=2):
            if name == "workflow":
                repository = "app" if payload["sourceUrl"].startswith("https://github.com/source/app") else "other"
                catalog = make_catalog(repository=f"source/{repository}")
                return {"success": True, "catalogs": [{"sourceUrl": payload["sourceUrl"], "catalog": catalog}]}
            publisher_calls.append(payload)
            return {"success": True, "status": "created"}

        result = run_manifest(
            object(), {"sourceUrl": MANIFEST_URL}, "workflow", "publisher", "gpt-4o",
            manifest_loader=lambda blob: two_repo_manifest, commit_resolver=lambda entry: NEW_SHA, invoker=invoke,
        )
        self.assertTrue(result["success"])
        self.assertEqual(1, len(publisher_calls))
        self.assertEqual(2, len(publisher_calls[0]["catalogs"]))
        self.assertEqual(2, result["generatedCatalogCount"])

    def test_run_manifest_reports_failed_status_when_no_catalog_succeeds(self):
        def invoke(project, name, model, payload, max_attempts=2):
            return {"success": False, "generationErrors": [{"message": "No local dev config found."}], "catalogs": []}

        result = run_manifest(
            object(), {"sourceUrl": MANIFEST_URL}, "workflow", "publisher", "gpt-4o",
            manifest_loader=lambda blob: manifest(), commit_resolver=lambda entry: NEW_SHA, invoker=invoke,
        )
        self.assertFalse(result["success"])
        self.assertEqual("failed", result["status"])
        self.assertEqual("workflow", result["failures"][0]["stage"])
        self.assertIsNone(result["pullRequest"])


if __name__ == "__main__":
    unittest.main()
