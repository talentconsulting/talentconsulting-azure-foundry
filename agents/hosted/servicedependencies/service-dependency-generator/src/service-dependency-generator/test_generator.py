import json
import unittest

from generator import GenerationError, SourceLocation, generate_from_text, parse_input, source_prompt, validate_catalog


SOURCE = "https://github.com/source/app/tree/main/src"
FILES = ["https://github.com/source/app/blob/main/src/Clients/AccountsClient.cs"]
CATALOG = {
    "repository": "source/app",
    "ref": "main",
    "path": "src",
    "dependencies": [{
        "name": "Accounts API",
        "kind": "http-api",
        "classification": "internal",
        "direction": "outbound",
        "client": "AccountsClient",
        "technology": "HttpClient",
        "configurationKeys": ["AccountsApi:BaseUrl"],
        "authentication": {"type": "oauth2", "configurationKeys": ["AccountsApi:Identifier"]},
        "operations": [{
            "method": "GET", "methodName": "GetAccount", "path": "/accounts/{id}",
            "sourceFile": "src/Clients/AccountsClient.cs",
        }],
        "resources": [],
        "evidence": [{"sourceFile": "src/Clients/AccountsClient.cs", "reason": "Typed HTTP client registration."}],
        "confidence": "high",
    }],
}


class GeneratorTests(unittest.TestCase):
    def test_input_requires_selected_same_repository_files(self):
        self.assertEqual(FILES, parse_input(json.dumps({"sourceUrl": SOURCE, "sourceFiles": FILES}))["sourceFiles"])
        with self.assertRaises(GenerationError):
            parse_input(json.dumps({"sourceUrl": SOURCE}))
        with self.assertRaises(GenerationError):
            parse_input(json.dumps({"sourceUrl": SOURCE, "sourceFiles": ["https://github.com/other/app/blob/main/X.cs"]}))

    def test_source_prompt_explicitly_requests_json(self):
        prompt = source_prompt(SourceLocation("source", "app", "main", "src"), {"src/Client.cs": "HttpClient client;"})
        self.assertIn("JSON", prompt)

    def test_validates_catalog_contract_and_source_evidence(self):
        result = validate_catalog(
            json.loads(json.dumps(CATALOG)),
            SourceLocation("source", "app", "main", "src"),
            {"src/Clients/AccountsClient.cs"},
        )
        self.assertEqual("Accounts API", result["dependencies"][0]["name"])
        bad = json.loads(json.dumps(CATALOG))
        bad["dependencies"][0]["evidence"][0]["sourceFile"] = "src/NotSupplied.cs"
        with self.assertRaisesRegex(GenerationError, "supplied source"):
            validate_catalog(bad, source_paths={"src/Clients/AccountsClient.cs"})

    def test_operations_require_a_methodname_field(self):
        bad = json.loads(json.dumps(CATALOG))
        del bad["dependencies"][0]["operations"][0]["methodName"]
        with self.assertRaisesRegex(GenerationError, "invalid shape"):
            validate_catalog(bad, source_paths={"src/Clients/AccountsClient.cs"})

    def test_operations_methodname_may_be_null(self):
        catalog = json.loads(json.dumps(CATALOG))
        catalog["dependencies"][0]["operations"][0]["methodName"] = None
        result = validate_catalog(catalog, source_paths={"src/Clients/AccountsClient.cs"})
        self.assertIsNone(result["dependencies"][0]["operations"][0]["methodName"])

    def test_a_redis_cache_dependency_is_kept_in_the_output(self):
        catalog = json.loads(json.dumps(CATALOG))
        catalog["dependencies"].append({
            "name": "Redis", "kind": "cache", "classification": "internal", "direction": "outbound",
            "client": None, "technology": "StackExchange.Redis",
            "configurationKeys": ["Redis:ConnectionString"],
            "authentication": {"type": None, "configurationKeys": []},
            "operations": [], "resources": [],
            "evidence": [{
                "sourceFile": "src/Clients/AccountsClient.cs",
                "reason": "AddStackExchangeRedisCache registration found.",
            }],
            "confidence": "high",
        })
        result = validate_catalog(catalog, source_paths={"src/Clients/AccountsClient.cs"})
        names = {dependency["name"] for dependency in result["dependencies"]}
        self.assertIn("Redis", names)

    def test_rejects_literal_endpoint_hostnames(self):
        bad = json.loads(json.dumps(CATALOG))
        bad["dependencies"][0]["operations"][0]["path"] = "https://accounts.example/api"
        with self.assertRaisesRegex(GenerationError, "hostname"):
            validate_catalog(bad, source_paths={"src/Clients/AccountsClient.cs"})

    def test_filters_database_dependencies_from_model_output(self):
        catalog = json.loads(json.dumps(CATALOG))
        database = json.loads(json.dumps(CATALOG["dependencies"][0]))
        database.update({
            "name": "ProviderCommitmentsDbContext",
            "kind": "database",
            "client": "ProviderCommitmentsDbContext",
            "technology": "Entity Framework Core",
        })
        catalog["dependencies"].append(database)

        result = validate_catalog(catalog, source_paths={"src/Clients/AccountsClient.cs"})

        self.assertEqual(["Accounts API"], [dependency["name"] for dependency in result["dependencies"]])

    def test_generate_downloads_only_selected_files(self):
        loaded = []

        def load(location, files):
            loaded.extend(files)
            return {"src/Clients/AccountsClient.cs": "class AccountsClient { HttpClient client; }"}

        result = generate_from_text(
            json.dumps({"sourceUrl": SOURCE, "sourceFiles": FILES}),
            completion=lambda prompt: json.dumps(CATALOG),
            source_loader=load,
        )
        self.assertEqual(FILES, loaded)
        self.assertEqual("Accounts API", result["dependencies"][0]["name"])


if __name__ == "__main__":
    unittest.main()
