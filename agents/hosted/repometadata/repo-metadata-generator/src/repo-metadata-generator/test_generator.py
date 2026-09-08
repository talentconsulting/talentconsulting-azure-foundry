import unittest

from generator import (
    GenerationError,
    SourceLocation,
    _parse_bicep,
    _parse_terraform,
    generate_from_text,
    parse_input,
    validate_catalog,
)

SOURCE_URL = "https://github.com/owner/repo/tree/main/src"
LOCATION = SourceLocation("owner", "repo", "main", "src")
LAST_COMMIT_DATE = "2024-01-01T00:00:00Z"


def _commit_date_loader(location):
    return LAST_COMMIT_DATE


class ParseInputTests(unittest.TestCase):
    def test_requires_exactly_sourceUrl_and_sourceFiles(self):
        with self.assertRaises(GenerationError):
            parse_input("{}")

    def test_rejects_source_files_from_a_different_repository(self):
        payload = '{"sourceUrl":"%s","sourceFiles":["https://github.com/other/repo/blob/main/src/App.csproj"]}' % SOURCE_URL
        with self.assertRaises(GenerationError):
            parse_input(payload)

    def test_rejects_duplicate_source_files(self):
        blob = "https://github.com/owner/repo/blob/main/src/App/App.csproj"
        payload = '{"sourceUrl":"%s","sourceFiles":["%s","%s"]}' % (SOURCE_URL, blob, blob)
        with self.assertRaises(GenerationError):
            parse_input(payload)

    def test_accepts_valid_input(self):
        blob = "https://github.com/owner/repo/blob/main/src/App/App.csproj"
        parsed = parse_input('{"sourceUrl":"%s","sourceFiles":["%s"]}' % (SOURCE_URL, blob))
        self.assertEqual(parsed["location"], LOCATION)
        self.assertEqual(parsed["paths"], ["src/App/App.csproj"])


class ValidateCatalogTests(unittest.TestCase):
    def test_requires_exact_key_set(self):
        with self.assertRaises(GenerationError):
            validate_catalog({"repository": "owner/repo"})

    def test_rejects_missing_last_commit_date(self):
        catalog = {
            "repository": "owner/repo", "ref": "main", "path": "src",
            "projects": [], "sdks": [], "azureResources": [],
        }
        with self.assertRaises(GenerationError):
            validate_catalog(catalog)

    def test_rejects_empty_last_commit_date(self):
        catalog = {
            "repository": "owner/repo", "ref": "main", "path": "src", "lastCommitDate": "",
            "projects": [], "sdks": [], "azureResources": [],
        }
        with self.assertRaises(GenerationError):
            validate_catalog(catalog)

    def test_rejects_project_path_outside_source_paths(self):
        catalog = {
            "repository": "owner/repo", "ref": "main", "path": "src", "lastCommitDate": LAST_COMMIT_DATE,
            "projects": [{"path": "src/App/App.csproj", "targetFrameworks": ["net8.0"]}],
            "sdks": [], "azureResources": [],
        }
        with self.assertRaises(GenerationError):
            validate_catalog(catalog, source_paths=set())

    def test_rejects_azure_resource_path_outside_source_paths(self):
        catalog = {
            "repository": "owner/repo", "ref": "main", "path": "src", "lastCommitDate": LAST_COMMIT_DATE,
            "projects": [], "sdks": [],
            "azureResources": [{"path": "src/infra/main.bicep", "type": "Microsoft.Storage/storageAccounts", "name": "sa"}],
        }
        with self.assertRaises(GenerationError):
            validate_catalog(catalog, source_paths=set())

    def test_allows_multiple_azure_resources_sharing_one_path(self):
        # Unlike projects/sdks, many resources can legitimately come from the same IaC file --
        # this must not be treated as a duplicate-path error.
        catalog = {
            "repository": "owner/repo", "ref": "main", "path": "src", "lastCommitDate": LAST_COMMIT_DATE,
            "projects": [], "sdks": [],
            "azureResources": [
                {"path": "src/infra/main.bicep", "type": "Microsoft.Storage/storageAccounts", "name": "sa"},
                {"path": "src/infra/main.bicep", "type": "Microsoft.KeyVault/vaults", "name": "kv"},
            ],
        }
        result = validate_catalog(catalog, source_paths={"src/infra/main.bicep"})
        self.assertEqual(2, len(result["azureResources"]))

    def test_sorts_projects_sdks_and_azure_resources_by_path(self):
        catalog = {
            "repository": "owner/repo", "ref": "main", "path": "src", "lastCommitDate": LAST_COMMIT_DATE,
            "projects": [
                {"path": "src/Z/Z.csproj", "targetFrameworks": ["net8.0"]},
                {"path": "src/A/A.csproj", "targetFrameworks": ["net8.0"]},
            ],
            "sdks": [
                {"path": "src/Z/global.json", "version": "8.0.100"},
                {"path": "src/A/global.json", "version": "8.0.100"},
            ],
            "azureResources": [
                {"path": "src/Z/main.tf", "type": "azurerm_storage_account", "name": "z"},
                {"path": "src/A/main.bicep", "type": "Microsoft.Storage/storageAccounts", "name": None},
            ],
        }
        result = validate_catalog(catalog, source_paths={
            "src/Z/Z.csproj", "src/A/A.csproj", "src/Z/global.json", "src/A/global.json",
            "src/Z/main.tf", "src/A/main.bicep",
        })
        self.assertEqual([item["path"] for item in result["projects"]], ["src/A/A.csproj", "src/Z/Z.csproj"])
        self.assertEqual([item["path"] for item in result["sdks"]], ["src/A/global.json", "src/Z/global.json"])
        self.assertEqual([item["path"] for item in result["azureResources"]], ["src/A/main.bicep", "src/Z/main.tf"])
        self.assertEqual(result["lastCommitDate"], LAST_COMMIT_DATE)


class ParseBicepTests(unittest.TestCase):
    def test_simple_resource_with_literal_name(self):
        content = """
resource storageAccount 'Microsoft.Storage/storageAccounts@2023-01-01' = {
  name: 'mystorageacct'
  location: 'uksouth'
}
"""
        self.assertEqual(
            _parse_bicep(content),
            [{"type": "Microsoft.Storage/storageAccounts", "name": "mystorageacct"}],
        )

    def test_non_literal_name_yields_none(self):
        content = """
resource storageAccount 'Microsoft.Storage/storageAccounts@2023-01-01' = {
  name: '${prefix}-sa'
  location: 'uksouth'
}
"""
        self.assertEqual(
            _parse_bicep(content),
            [{"type": "Microsoft.Storage/storageAccounts", "name": None}],
        )

    def test_existing_resource_is_still_included(self):
        content = """
resource sharedVault 'Microsoft.KeyVault/vaults@2023-07-01' existing = {
  name: 'shared-kv'
}
"""
        self.assertEqual(
            _parse_bicep(content),
            [{"type": "Microsoft.KeyVault/vaults", "name": "shared-kv"}],
        )

    def test_nested_object_before_matching_close_does_not_truncate_the_block(self):
        # `name:` appears before the nested `sku: {...}` object. A naive non-greedy regex across
        # the whole declaration would stop at the *first* '}' it saw (sku's), and a brace-depth
        # bug would misplace the block boundary for whatever follows -- this checks that the
        # second resource's own type/name are still parsed correctly and not corrupted by the
        # first resource's internal nesting.
        content = """
resource sqlDb 'Microsoft.Sql/servers/databases@2023-05-01' = {
  name: 'orders-db'
  sku: {
    name: 'S0'
    tier: 'Standard'
  }
}
resource cache 'Microsoft.Cache/redis@2023-08-01' = {
  name: 'orders-cache'
}
"""
        self.assertEqual(
            _parse_bicep(content),
            [
                {"type": "Microsoft.Sql/servers/databases", "name": "orders-db"},
                {"type": "Microsoft.Cache/redis", "name": "orders-cache"},
            ],
        )

    def test_malformed_content_returns_empty_list(self):
        self.assertEqual(_parse_bicep("this is not valid bicep content { with random braces"), [])
        self.assertEqual(_parse_bicep(""), [])


class ParseTerraformTests(unittest.TestCase):
    def test_simple_resource_with_literal_name(self):
        content = """
resource "azurerm_storage_account" "sa" {
  name                = "mystorageacct"
  location            = "uksouth"
}
"""
        self.assertEqual(
            _parse_terraform(content),
            [{"type": "azurerm_storage_account", "name": "mystorageacct"}],
        )

    def test_non_literal_name_yields_none(self):
        content = """
resource "azurerm_storage_account" "sa" {
  name = "${var.prefix}-sa"
}
"""
        self.assertEqual(
            _parse_terraform(content),
            [{"type": "azurerm_storage_account", "name": None}],
        )

    def test_meta_arguments_before_name_do_not_break_parsing(self):
        # Terraform has no "existing" resource concept the way Bicep does, but a resource block
        # commonly carries meta-arguments (count/for_each/provider) ahead of its other
        # attributes -- this checks that extra content in the block still resolves the name.
        content = """
resource "azurerm_storage_account" "sa" {
  count = 1
  name  = "conditional-sa"
}
"""
        self.assertEqual(
            _parse_terraform(content),
            [{"type": "azurerm_storage_account", "name": "conditional-sa"}],
        )

    def test_nested_block_before_matching_close_does_not_truncate_the_block(self):
        content = """
resource "azurerm_storage_account" "sa" {
  name = "orders-storage"
  network_rules {
    default_action = "Deny"
  }
}
resource "azurerm_redis_cache" "cache" {
  name = "orders-cache"
}
"""
        self.assertEqual(
            _parse_terraform(content),
            [
                {"type": "azurerm_storage_account", "name": "orders-storage"},
                {"type": "azurerm_redis_cache", "name": "orders-cache"},
            ],
        )

    def test_malformed_content_returns_empty_list(self):
        self.assertEqual(_parse_terraform("this is not valid terraform content { with random braces"), [])
        self.assertEqual(_parse_terraform(""), [])

    def test_non_azurerm_resource_type_is_excluded(self):
        content = 'resource "aws_s3_bucket" "b" {\n  bucket = "irrelevant"\n}\n'
        self.assertEqual(_parse_terraform(content), [])


class GenerateFromTextTests(unittest.TestCase):
    def test_single_target_framework(self):
        def source_loader(location, paths):
            self.assertEqual(location, LOCATION)
            return {"src/App/App.csproj": "<Project Sdk=\"Microsoft.NET.Sdk\"><PropertyGroup><TargetFramework>net8.0</TargetFramework></PropertyGroup></Project>"}

        blob = "https://github.com/owner/repo/blob/main/src/App/App.csproj"
        result = generate_from_text(
            '{"sourceUrl":"%s","sourceFiles":["%s"]}' % (SOURCE_URL, blob),
            source_loader=source_loader,
            commit_date_loader=_commit_date_loader,
        )
        self.assertEqual(result["projects"], [{"path": "src/App/App.csproj", "targetFrameworks": ["net8.0"]}])
        self.assertEqual(result["sdks"], [])
        self.assertEqual(result["lastCommitDate"], LAST_COMMIT_DATE)

    def test_multi_target_framework_semicolon_split(self):
        def source_loader(location, paths):
            return {"src/App/App.csproj": "<Project><PropertyGroup><TargetFrameworks>net8.0;net472</TargetFrameworks></PropertyGroup></Project>"}

        blob = "https://github.com/owner/repo/blob/main/src/App/App.csproj"
        result = generate_from_text(
            '{"sourceUrl":"%s","sourceFiles":["%s"]}' % (SOURCE_URL, blob),
            source_loader=source_loader,
            commit_date_loader=_commit_date_loader,
        )
        self.assertEqual(result["projects"][0]["targetFrameworks"], ["net8.0", "net472"])

    def test_legacy_target_framework_version(self):
        def source_loader(location, paths):
            return {
                "src/App/App.csproj": (
                    "<Project xmlns=\"http://schemas.microsoft.com/developer/msbuild/2003\">"
                    "<PropertyGroup><TargetFrameworkVersion>v4.7.2</TargetFrameworkVersion></PropertyGroup></Project>"
                )
            }

        blob = "https://github.com/owner/repo/blob/main/src/App/App.csproj"
        result = generate_from_text(
            '{"sourceUrl":"%s","sourceFiles":["%s"]}' % (SOURCE_URL, blob),
            source_loader=source_loader,
            commit_date_loader=_commit_date_loader,
        )
        self.assertEqual(result["projects"][0]["targetFrameworks"], ["v4.7.2"])

    def test_csproj_with_no_recognizable_framework_yields_empty_list(self):
        def source_loader(location, paths):
            return {"src/App/App.csproj": "<Project><PropertyGroup><OutputType>Exe</OutputType></PropertyGroup></Project>"}

        blob = "https://github.com/owner/repo/blob/main/src/App/App.csproj"
        result = generate_from_text(
            '{"sourceUrl":"%s","sourceFiles":["%s"]}' % (SOURCE_URL, blob),
            source_loader=source_loader,
            commit_date_loader=_commit_date_loader,
        )
        self.assertEqual(result["projects"], [{"path": "src/App/App.csproj", "targetFrameworks": []}])

    def test_global_json_sdk_version_and_roll_forward(self):
        def source_loader(location, paths):
            return {"src/global.json": '{"sdk":{"version":"8.0.100","rollForward":"latestMinor"}}'}

        blob = "https://github.com/owner/repo/blob/main/src/global.json"
        result = generate_from_text(
            '{"sourceUrl":"%s","sourceFiles":["%s"]}' % (SOURCE_URL, blob),
            source_loader=source_loader,
            commit_date_loader=_commit_date_loader,
        )
        self.assertEqual(result["sdks"], [{"path": "src/global.json", "version": "8.0.100", "rollForward": "latestMinor"}])

    def test_global_json_without_sdk_key_is_omitted(self):
        def source_loader(location, paths):
            return {"src/global.json": "{}"}

        blob = "https://github.com/owner/repo/blob/main/src/global.json"
        result = generate_from_text(
            '{"sourceUrl":"%s","sourceFiles":["%s"]}' % (SOURCE_URL, blob),
            source_loader=source_loader,
            commit_date_loader=_commit_date_loader,
        )
        self.assertEqual(result["sdks"], [])

    def test_malformed_xml_yields_empty_target_frameworks_not_an_error(self):
        def source_loader(location, paths):
            return {"src/App/App.csproj": "<Project><Unclosed>"}

        blob = "https://github.com/owner/repo/blob/main/src/App/App.csproj"
        result = generate_from_text(
            '{"sourceUrl":"%s","sourceFiles":["%s"]}' % (SOURCE_URL, blob),
            source_loader=source_loader,
            commit_date_loader=_commit_date_loader,
        )
        self.assertEqual(result["projects"], [{"path": "src/App/App.csproj", "targetFrameworks": []}])

    def test_commit_date_loader_result_flows_into_last_commit_date(self):
        def source_loader(location, paths):
            return {"src/global.json": '{"sdk":{"version":"8.0.100"}}'}

        blob = "https://github.com/owner/repo/blob/main/src/global.json"
        result = generate_from_text(
            '{"sourceUrl":"%s","sourceFiles":["%s"]}' % (SOURCE_URL, blob),
            source_loader=source_loader,
            commit_date_loader=lambda location: "2023-06-15T12:00:00Z",
        )
        self.assertEqual(result["lastCommitDate"], "2023-06-15T12:00:00Z")

    def test_commit_date_loader_failure_surfaces_as_commit_lookup_failed(self):
        def source_loader(location, paths):
            return {"src/global.json": '{"sdk":{"version":"8.0.100"}}'}

        def failing_commit_date_loader(location):
            raise GenerationError("commit_lookup_failed", "Unable to determine the last commit date for owner/repo@main.")

        blob = "https://github.com/owner/repo/blob/main/src/global.json"
        with self.assertRaises(GenerationError) as context:
            generate_from_text(
                '{"sourceUrl":"%s","sourceFiles":["%s"]}' % (SOURCE_URL, blob),
                source_loader=source_loader,
                commit_date_loader=failing_commit_date_loader,
            )
        self.assertEqual(context.exception.code, "commit_lookup_failed")

    def test_bicep_and_terraform_feed_into_one_combined_sorted_azure_resources_list(self):
        def source_loader(location, paths):
            return {
                "src/infra/main.bicep": (
                    "resource sa 'Microsoft.Storage/storageAccounts@2023-01-01' = {\n"
                    "  name: 'appstorage'\n"
                    "}\n"
                ),
                "src/infra/network.tf": (
                    'resource "azurerm_virtual_network" "vnet" {\n'
                    '  name = "app-vnet"\n'
                    "}\n"
                ),
            }

        bicep_blob = "https://github.com/owner/repo/blob/main/src/infra/main.bicep"
        tf_blob = "https://github.com/owner/repo/blob/main/src/infra/network.tf"
        result = generate_from_text(
            '{"sourceUrl":"%s","sourceFiles":["%s","%s"]}' % (SOURCE_URL, bicep_blob, tf_blob),
            source_loader=source_loader,
            commit_date_loader=_commit_date_loader,
        )
        self.assertEqual(
            result["azureResources"],
            [
                {"path": "src/infra/main.bicep", "type": "Microsoft.Storage/storageAccounts", "name": "appstorage"},
                {"path": "src/infra/network.tf", "type": "azurerm_virtual_network", "name": "app-vnet"},
            ],
        )


if __name__ == "__main__":
    unittest.main()
