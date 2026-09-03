import io
import unittest
import zipfile

from scanner import ScanError, parse_source_url, scan

SOURCE = "https://github.com/owner/repo/tree/main/src"


def archive(files: dict[str, str]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as zip_file:
        for path, content in files.items():
            zip_file.writestr(f"repo-main/{path}", content)
    return buffer.getvalue()


class ParseSourceUrlTests(unittest.TestCase):
    def test_parses_owner_repository_ref_and_path(self):
        location = parse_source_url(SOURCE)
        self.assertEqual(location.owner, "owner")
        self.assertEqual(location.repository, "repo")
        self.assertEqual(location.ref, "main")
        self.assertEqual(location.base_path, "src")

    def test_rejects_non_tree_url(self):
        with self.assertRaises(ScanError):
            parse_source_url("https://github.com/owner/repo/blob/main/src/file.cs")


class ScanTests(unittest.TestCase):
    def test_selects_csproj_and_global_json(self):
        result = scan(SOURCE, archive({
            "src/App/App.csproj": "<Project />",
            "src/global.json": "{}",
            "src/README.md": "not relevant",
        }))
        self.assertEqual(
            result["dotnetVersionFiles"],
            [
                "https://github.com/owner/repo/blob/main/src/App/App.csproj",
                "https://github.com/owner/repo/blob/main/src/global.json",
            ],
        )
        self.assertEqual(result["excludedFiles"], [])

    def test_ignores_build_and_package_directories(self):
        result = scan(SOURCE, archive({
            "src/App/obj/App.csproj": "<Project />",
            "src/App/bin/Debug/App.csproj": "<Project />",
            "src/packages/Some.Package/Some.Package.csproj": "<Project />",
        }))
        self.assertEqual(result["dotnetVersionFiles"], [])

    def test_restricts_to_files_under_requested_path(self):
        result = scan(SOURCE, archive({
            "other/App.csproj": "<Project />",
            "src/App/App.csproj": "<Project />",
        }))
        self.assertEqual(
            result["dotnetVersionFiles"],
            ["https://github.com/owner/repo/blob/main/src/App/App.csproj"],
        )

    def test_excludes_non_utf8_files(self):
        result = scan(SOURCE, archive({}) )
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as zip_file:
            zip_file.writestr("repo-main/src/App/App.csproj", b"\xff\xfe\x00\x01")
        result = scan(SOURCE, buffer.getvalue())
        self.assertEqual(result["dotnetVersionFiles"], [])
        self.assertEqual(result["excludedFiles"], [{"path": "src/App/App.csproj", "reason": "not_utf8"}])

    def test_no_matching_files_is_a_valid_empty_result(self):
        result = scan(SOURCE, archive({"src/README.md": "hello"}))
        self.assertEqual(result, {"dotnetVersionFiles": [], "excludedFiles": []})


if __name__ == "__main__":
    unittest.main()
