import unittest

from workflow import WorkflowError, merge_catalogs, parse_workflow_request, run_workflow


SOURCE = "https://github.com/source/app/tree/main/src"
FILES = [f"https://github.com/source/app/blob/main/src/Clients/Client{index}.cs" for index in range(2)]


def dependency(name="Accounts API"):
    return {
        "name": name,
        "kind": "http-api",
        "classification": "unknown",
        "direction": "outbound",
        "client": "AccountsClient",
        "technology": "HttpClient",
        "configurationKeys": ["AccountsApi:BaseUrl"],
        "authentication": {"type": None, "configurationKeys": []},
        "operations": [],
        "resources": [],
        "evidence": [{"sourceFile": "src/Clients/Client0.cs", "reason": "HTTP client"}],
        "confidence": "medium",
    }


def catalog(items=None):
    return {"repository": "source/app", "ref": "main", "path": "src", "dependencies": items or []}


class WorkflowTests(unittest.TestCase):
    def test_direct_request_requires_target_repository(self):
        with self.assertRaisesRegex(WorkflowError, "targetRepository"):
            parse_workflow_request('{"sourceUrl":"%s"}' % SOURCE)
        self.assertTrue(parse_workflow_request('{"sourceUrl":"%s","deferPublication":true}' % SOURCE)["deferPublication"])

    def test_deferred_workflow_batches_and_merges(self):
        def invoke(project, name, model, payload, max_attempts=2):
            if name == "discovery":
                return {"sourceFiles": FILES, "excludedFiles": []}
            if name == "generator":
                item = dependency("Accounts API")
                item["evidence"] = [{"sourceFile": payload["sourceFiles"][0].split("/blob/main/")[1], "reason": "HTTP client"}]
                return catalog([item])
            raise AssertionError(name)

        result = run_workflow(
            object(), {"sourceUrl": SOURCE, "deferPublication": True},
            "discovery", "generator", "publisher", "gpt-4o", generator_batch_size=1, invoker=invoke,
        )
        self.assertTrue(result["success"])
        self.assertEqual(1, len(result["catalogs"][0]["catalog"]["dependencies"]))
        self.assertEqual(2, len(result["catalogs"][0]["catalog"]["dependencies"][0]["evidence"]))

    def test_merge_enriches_unknown_values_and_unions_evidence(self):
        first = dependency()
        second = dependency()
        second["classification"] = "internal"
        second["authentication"] = {"type": "oauth2", "configurationKeys": ["AccountsApi:Identifier"]}
        second["evidence"] = [{"sourceFile": "src/Startup.cs", "reason": "Typed client registration"}]
        merged = merge_catalogs([catalog([first]), catalog([second])])["dependencies"][0]
        self.assertEqual("internal", merged["classification"])
        self.assertEqual("oauth2", merged["authentication"]["type"])
        self.assertEqual(2, len(merged["evidence"]))

    def test_merge_keeps_first_scalar_when_batches_format_api_metadata_differently(self):
        first = dependency("ApprovalsOuterApiClient")
        first["authentication"] = {"type": "API Key", "configurationKeys": ["ApprovalsApi:Key"]}
        second = dependency("ApprovalsOuterApiClient")
        second["technology"] = ".NET HttpClient"
        second["authentication"] = {"type": "api-key", "configurationKeys": ["ApprovalsApi.Key"]}
        second["evidence"] = [{"sourceFile": "src/Startup.cs", "reason": "Typed client registration"}]

        merged = merge_catalogs([catalog([first]), catalog([second])])["dependencies"][0]

        self.assertEqual("HttpClient", merged["technology"])
        self.assertEqual("API Key", merged["authentication"]["type"])
        self.assertEqual(["ApprovalsApi.Key", "ApprovalsApi:Key"], merged["authentication"]["configurationKeys"])
        self.assertEqual(2, len(merged["evidence"]))

    def test_failed_batch_fails_closed(self):
        publisher_called = False

        def invoke(project, name, model, payload, max_attempts=2):
            nonlocal publisher_called
            if name == "discovery":
                return {"sourceFiles": FILES, "excludedFiles": []}
            if name == "publisher":
                publisher_called = True
            if payload["sourceFiles"] == FILES[1:]:
                return {"error": {"code": "invalid_model_output", "message": "bad catalog"}}
            return catalog([dependency()])

        result = run_workflow(
            object(), {"sourceUrl": SOURCE, "deferPublication": True},
            "discovery", "generator", "publisher", "gpt-4o", generator_batch_size=1, invoker=invoke,
        )
        self.assertFalse(result["success"])
        self.assertEqual("partial_generation_failed", result["errors"][0]["code"])
        self.assertEqual([], result["catalogs"])
        self.assertFalse(publisher_called)

    def test_empty_catalog_fails(self):
        def invoke(project, name, model, payload, max_attempts=2):
            if name == "discovery":
                return {"sourceFiles": FILES[:1], "excludedFiles": []}
            return catalog()

        result = run_workflow(
            object(), {"sourceUrl": SOURCE, "deferPublication": True},
            "discovery", "generator", "publisher", "gpt-4o", invoker=invoke,
        )
        self.assertFalse(result["success"])
        self.assertEqual("no_dependencies_found", result["errors"][0]["code"])

    def test_direct_workflow_publishes_deterministic_path(self):
        def invoke(project, name, model, payload, max_attempts=2):
            if name == "discovery":
                return {"sourceFiles": FILES[:1], "excludedFiles": []}
            if name == "generator":
                return catalog([dependency()])
            self.assertEqual("app/service-dependencies/service-dependencies.json", payload["catalogs"][0]["targetPath"])
            return {"success": True, "status": "created"}

        result = run_workflow(
            object(), {"sourceUrl": SOURCE, "targetRepository": "target/catalog"},
            "discovery", "generator", "publisher", "gpt-4o", invoker=invoke,
        )
        self.assertTrue(result["success"])


if __name__ == "__main__":
    unittest.main()
