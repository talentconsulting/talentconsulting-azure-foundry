import unittest

from generator import (
    GenerationError,
    SourceLocation,
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
            "projects": [], "sdks": [],
        }
        with self.assertRaises(GenerationError):
            validate_catalog(catalog)

    def test_rejects_empty_last_commit_date(self):
        catalog = {
            "repository": "owner/repo", "ref": "main", "path": "src", "lastCommitDate": "",
            "projects": [], "sdks": [],
        }
        with self.assertRaises(GenerationError):
            validate_catalog(catalog)

    def test_rejects_project_path_outside_source_paths(self):
        catalog = {
            "repository": "owner/repo", "ref": "main", "path": "src", "lastCommitDate": LAST_COMMIT_DATE,
            "projects": [{"path": "src/App/App.csproj", "targetFrameworks": ["net8.0"]}],
            "sdks": [],
        }
        with self.assertRaises(GenerationError):
            validate_catalog(catalog, source_paths=set())

    def test_sorts_projects_and_sdks_by_path(self):
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
        }
        result = validate_catalog(catalog, source_paths={"src/Z/Z.csproj", "src/A/A.csproj", "src/Z/global.json", "src/A/global.json"})
        self.assertEqual([item["path"] for item in result["projects"]], ["src/A/A.csproj", "src/Z/Z.csproj"])
        self.assertEqual([item["path"] for item in result["sdks"]], ["src/A/global.json", "src/Z/global.json"])
        self.assertEqual(result["lastCommitDate"], LAST_COMMIT_DATE)


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


if __name__ == "__main__":
    unittest.main()
