import json
import unittest
from unittest.mock import patch

from workflow import WorkflowError, merge_catalogs, parse_workflow_request, run_workflow


SOURCE = "https://github.com/source/app/tree/main/src"
LAST_COMMIT_DATE = "2024-01-01T00:00:00Z"


def _file(index: int) -> str:
    return f"https://github.com/source/app/blob/main/src/App{index}/App{index}.csproj"


def _catalog(project_path: str, target_frameworks: list[str], azure_resources: list[dict] | None = None) -> dict:
    return {
        "repository": "source/app",
        "ref": "main",
        "path": "src",
        "lastCommitDate": LAST_COMMIT_DATE,
        "projects": [{"path": project_path, "targetFrameworks": target_frameworks}],
        "sdks": [],
        "azureResources": azure_resources if azure_resources is not None else [],
    }


class WorkflowRequestTests(unittest.TestCase):
    def test_parse_workflow_request_requires_source_url_and_defaults_defer_publication_false(self):
        with self.assertRaisesRegex(WorkflowError, "sourceUrl"):
            parse_workflow_request(json.dumps({"targetRepository": "t/r"}))
        with self.assertRaisesRegex(WorkflowError, "targetRepository"):
            parse_workflow_request(json.dumps({"sourceUrl": SOURCE}))

    def test_parse_workflow_request_requires_target_repository_when_not_deferred(self):
        with self.assertRaisesRegex(WorkflowError, "targetRepository"):
            parse_workflow_request(json.dumps({"sourceUrl": SOURCE, "deferPublication": False}))
        parsed = parse_workflow_request(json.dumps({"sourceUrl": SOURCE, "deferPublication": True}))
        self.assertEqual(SOURCE, parsed["sourceUrl"])
        self.assertTrue(parsed["deferPublication"])


class RunWorkflowTests(unittest.TestCase):
    def test_run_workflow_batches_files_and_merges_catalogs(self):
        files = [_file(index) for index in range(7)]
        discovery = {"repoMetadataFiles": files, "excludedFiles": []}
        generator_calls = []

        def invoke(project, name, model, payload, max_attempts=2):
            if name == "discovery":
                self.assertEqual({"sourceUrl": SOURCE}, payload)
                return discovery
            self.assertEqual("generator", name)
            generator_calls.append(payload["sourceFiles"])
            index = len(generator_calls)
            return _catalog(f"src/App{index}/App{index}.csproj", ["net8.0"])

        result = run_workflow(
            object(),
            {"sourceUrl": SOURCE, "deferPublication": True},
            "discovery",
            "generator",
            "pr_creator",
            "gpt-4o",
            generator_batch_size=5,
            invoker=invoke,
        )

        self.assertTrue(result["success"])
        self.assertEqual([files[0:5], files[5:7]], generator_calls)
        paths = sorted(project["path"] for project in result["catalogs"][0]["catalog"]["projects"])
        self.assertEqual(["src/App1/App1.csproj", "src/App2/App2.csproj"], paths)
        self.assertEqual(LAST_COMMIT_DATE, result["catalogs"][0]["catalog"]["lastCommitDate"])

    def test_run_workflow_merge_dedupes_by_path_first_wins_with_warning(self):
        # Two distinct discovered files whose generator batches happen to report the same
        # project path -- discovery itself guarantees unique URLs, so this simulates a
        # defensive edge case in merge_catalogs rather than something discovery would produce.
        files = [_file(0), _file(1)]
        discovery = {"repoMetadataFiles": files, "excludedFiles": []}
        calls = []

        def invoke(project, name, model, payload, max_attempts=2):
            if name == "discovery":
                return discovery
            calls.append(payload["sourceFiles"])
            frameworks = ["net8.0"] if len(calls) == 1 else ["net9.0"]
            return _catalog("src/App0/App0.csproj", frameworks)

        result = run_workflow(
            object(),
            {"sourceUrl": SOURCE, "deferPublication": True},
            "discovery",
            "generator",
            "pr_creator",
            "gpt-4o",
            generator_batch_size=1,
            invoker=invoke,
        )

        self.assertTrue(result["success"])
        projects = result["catalogs"][0]["catalog"]["projects"]
        self.assertEqual(1, len(projects))
        self.assertEqual(["net8.0"], projects[0]["targetFrameworks"])
        self.assertEqual(1, len(result["generationErrors"]))
        self.assertEqual("DuplicateProject", result["generationErrors"][0]["errorType"])

    def test_run_workflow_allows_empty_discovery_result(self):
        calls = []

        def invoke(project, name, model, payload, max_attempts=2):
            calls.append(name)
            if name == "discovery":
                return {"repoMetadataFiles": [], "excludedFiles": []}
            raise AssertionError("generator must not be called when discovery finds nothing")

        with patch("workflow._fetch_last_commit_date", return_value=LAST_COMMIT_DATE) as commit_date_loader:
            result = run_workflow(
                object(),
                {"sourceUrl": SOURCE, "deferPublication": True},
                "discovery",
                "generator",
                "pr_creator",
                "gpt-4o",
                invoker=invoke,
            )
            commit_date_loader.assert_called_once_with("source", "app", "main")

        self.assertTrue(result["success"])
        self.assertEqual(["discovery"], calls)
        catalog = result["catalogs"][0]["catalog"]
        self.assertEqual([], catalog["projects"])
        self.assertEqual([], catalog["sdks"])
        self.assertEqual([], catalog["azureResources"])
        self.assertEqual("source/app", catalog["repository"])
        self.assertEqual("main", catalog["ref"])
        self.assertEqual("src", catalog["path"])
        self.assertEqual(LAST_COMMIT_DATE, catalog["lastCommitDate"])
        self.assertEqual(0, result["discoveredFileCount"])

    def test_run_workflow_surfaces_commit_lookup_failure_on_empty_discovery_result(self):
        def invoke(project, name, model, payload, max_attempts=2):
            if name == "discovery":
                return {"repoMetadataFiles": [], "excludedFiles": []}
            raise AssertionError("generator must not be called when discovery finds nothing")

        with patch("workflow._fetch_last_commit_date", side_effect=WorkflowError("commit_lookup_failed", "boom")):
            result = run_workflow(
                object(),
                {"sourceUrl": SOURCE, "deferPublication": True},
                "discovery",
                "generator",
                "pr_creator",
                "gpt-4o",
                invoker=invoke,
            )

        self.assertFalse(result["success"])
        self.assertEqual("commit_lookup_failed", result["errors"][0]["code"])

    def test_run_workflow_defers_publication_without_calling_pr_creator(self):
        discovery = {"repoMetadataFiles": [_file(0)], "excludedFiles": []}
        catalog = _catalog("src/App0/App0.csproj", ["net8.0"])
        calls = []

        def invoke(project, name, model, payload, max_attempts=2):
            calls.append(name)
            if name == "discovery":
                return discovery
            if name == "generator":
                return catalog
            raise AssertionError("pr-creator must not be called when deferPublication is true")

        result = run_workflow(
            object(),
            {"sourceUrl": SOURCE, "deferPublication": True},
            "discovery",
            "generator",
            "pr_creator",
            "gpt-4o",
            invoker=invoke,
        )

        self.assertTrue(result["success"])
        self.assertIsNone(result["pullRequest"])
        self.assertEqual(["discovery", "generator"], calls)

    def test_run_workflow_calls_pr_creator_once_when_not_deferred(self):
        discovery = {"repoMetadataFiles": [_file(0)], "excludedFiles": []}
        catalog = _catalog("src/App0/App0.csproj", ["net8.0"])
        calls = []

        def invoke(project, name, model, payload, max_attempts=2):
            calls.append(name)
            if name == "discovery":
                return discovery
            if name == "generator":
                return catalog
            self.assertEqual(1, max_attempts)
            self.assertEqual("target/repo", payload["repository"])
            self.assertEqual(
                "app/repo-metadata/repo-metadata.json",
                payload["catalogs"][0]["targetPath"],
            )
            self.assertEqual(SOURCE, payload["catalogs"][0]["sourceUrl"])
            return {"success": True, "status": "created"}

        result = run_workflow(
            object(),
            {"sourceUrl": SOURCE, "targetRepository": "target/repo"},
            "discovery",
            "generator",
            "pr_creator",
            "gpt-4o",
            invoker=invoke,
        )

        self.assertTrue(result["success"])
        self.assertEqual(["discovery", "generator", "pr_creator"], calls)

    def test_run_workflow_reports_generation_failed_when_all_batches_fail_and_files_were_discovered(self):
        files = [_file(0), _file(1)]
        discovery = {"repoMetadataFiles": files, "excludedFiles": []}

        def invoke(project, name, model, payload, max_attempts=2):
            if name == "discovery":
                return discovery
            return {"error": {"code": "invalid_model_output", "message": "bad output"}}

        result = run_workflow(
            object(),
            {"sourceUrl": SOURCE, "deferPublication": True},
            "discovery",
            "generator",
            "pr_creator",
            "gpt-4o",
            generator_batch_size=1,
            invoker=invoke,
        )

        self.assertFalse(result["success"])
        self.assertEqual(0, result["generatedCatalogCount"])
        self.assertEqual("generation_failed", result["errors"][0]["code"])
        self.assertEqual(2, len(result["generationErrors"]))


class MergeCatalogsTests(unittest.TestCase):
    def test_merge_catalogs_combines_disjoint_projects_and_sdks(self):
        first = {
            "repository": "o/r", "ref": "main", "path": "p", "lastCommitDate": LAST_COMMIT_DATE,
            "projects": [{"path": "src/App1/App1.csproj", "targetFrameworks": ["net8.0"]}],
            "sdks": [{"path": "src/global.json", "version": "8.0.100"}],
            "azureResources": [],
        }
        second = {
            "repository": "o/r", "ref": "main", "path": "p", "lastCommitDate": LAST_COMMIT_DATE,
            "projects": [{"path": "src/App2/App2.csproj", "targetFrameworks": ["net9.0"]}],
            "sdks": [],
            "azureResources": [],
        }

        merged, warnings = merge_catalogs([first, second])

        self.assertEqual("o/r", merged["repository"])
        self.assertEqual([], warnings)
        self.assertEqual(
            ["src/App1/App1.csproj", "src/App2/App2.csproj"],
            [item["path"] for item in merged["projects"]],
        )
        self.assertEqual([{"path": "src/global.json", "version": "8.0.100"}], merged["sdks"])
        self.assertEqual(LAST_COMMIT_DATE, merged["lastCommitDate"])

        with self.assertRaisesRegex(WorkflowError, "disagree"):
            merge_catalogs([first, {**second, "path": "other"}])

    def test_merge_catalogs_rejects_mismatched_last_commit_date(self):
        first = {
            "repository": "o/r", "ref": "main", "path": "p", "lastCommitDate": LAST_COMMIT_DATE,
            "projects": [{"path": "src/App1/App1.csproj", "targetFrameworks": ["net8.0"]}],
            "sdks": [],
            "azureResources": [],
        }
        second = {**first, "lastCommitDate": "2024-02-02T00:00:00Z"}

        with self.assertRaisesRegex(WorkflowError, "disagree"):
            merge_catalogs([first, second])

    def test_merge_catalogs_dedupes_identical_project_without_warning(self):
        catalog = {
            "repository": "o/r", "ref": "main", "path": "p", "lastCommitDate": LAST_COMMIT_DATE,
            "projects": [{"path": "src/App/App.csproj", "targetFrameworks": ["net8.0"]}],
            "sdks": [{"path": "src/global.json", "version": "8.0.100"}],
            "azureResources": [],
        }

        merged, warnings = merge_catalogs([catalog, catalog])

        self.assertEqual([], warnings)
        self.assertEqual(1, len(merged["projects"]))
        self.assertEqual(1, len(merged["sdks"]))

    def test_merge_catalogs_combines_azure_resources_from_every_batch_without_dedup(self):
        # azureResources has no single-value-per-path invariant like projects/sdks -- a batch
        # just contributes whatever resources its files contained, and repeats across batches
        # (e.g. the same file appearing in two batches, or two files declaring the same-looking
        # resource) are kept, not collapsed.
        first = {
            "repository": "o/r", "ref": "main", "path": "p", "lastCommitDate": LAST_COMMIT_DATE,
            "projects": [], "sdks": [],
            "azureResources": [
                {"path": "src/infra/main.bicep", "type": "Microsoft.Storage/storageAccounts", "name": "sa"},
                {"path": "src/infra/main.bicep", "type": "Microsoft.KeyVault/vaults", "name": "kv"},
            ],
        }
        second = {
            "repository": "o/r", "ref": "main", "path": "p", "lastCommitDate": LAST_COMMIT_DATE,
            "projects": [], "sdks": [],
            "azureResources": [
                {"path": "src/infra/network.tf", "type": "azurerm_virtual_network", "name": "vnet"},
                {"path": "src/infra/main.bicep", "type": "Microsoft.Storage/storageAccounts", "name": "sa"},
            ],
        }

        merged, warnings = merge_catalogs([first, second])

        self.assertEqual([], warnings)
        self.assertEqual(4, len(merged["azureResources"]))
        # Sorted by (path.lower(), type, name or "") -- "Microsoft.KeyVault/..." sorts before
        # "Microsoft.Storage/..." within the same path, and the two identical storageAccounts
        # entries (one from each batch) are both kept.
        self.assertEqual(
            [
                {"path": "src/infra/main.bicep", "type": "Microsoft.KeyVault/vaults", "name": "kv"},
                {"path": "src/infra/main.bicep", "type": "Microsoft.Storage/storageAccounts", "name": "sa"},
                {"path": "src/infra/main.bicep", "type": "Microsoft.Storage/storageAccounts", "name": "sa"},
                {"path": "src/infra/network.tf", "type": "azurerm_virtual_network", "name": "vnet"},
            ],
            merged["azureResources"],
        )


if __name__ == "__main__":
    unittest.main()
