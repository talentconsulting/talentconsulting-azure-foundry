import io
import unittest
import zipfile

from scanner import scan


SOURCE = "https://github.com/source/app/tree/main/src"


def archive(files):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as output:
        for path, content in files.items():
            output.writestr(f"app-main/{path}", content)
    return buffer.getvalue()


class ScanTests(unittest.TestCase):
    def test_selects_architecture_evidence(self):
        result = scan(SOURCE, archive({
            "src/Program.cs": "var builder = WebApplication.CreateBuilder(args); builder.Services.AddDbContext<AppDbContext>();",
            "src/OrdersController.cs": "class OrdersController : ControllerBase { }",
            "src/appsettings.json": '{"ConnectionStrings":{"Sql":"redacted"}}',
            "src/Domain/Order.cs": "class Order { public long Id { get; set; } }",
        }))

        paths = result["sourceFiles"]
        self.assertTrue(any(path.endswith("src/Program.cs") for path in paths))
        self.assertTrue(any(path.endswith("src/OrdersController.cs") for path in paths))
        self.assertTrue(any(path.endswith("src/appsettings.json") for path in paths))
        self.assertFalse(any(path.endswith("src/Domain/Order.cs") for path in paths))

    def test_selects_infra_and_dependency_files(self):
        result = scan(SOURCE, archive({
            "src/app.csproj": "<Project><PackageReference Include=\"Microsoft.EntityFrameworkCore\" /></Project>",
            "src/infra/main.bicep": "resource database 'Microsoft.Sql/servers/databases@2022-05-01-preview' = {}",
            "src/docker-compose.yml": "services:\n  api:\n    image: app",
            "other/Program.cs": "WebApplication.CreateBuilder(args);",
        }))

        self.assertEqual([
            "https://github.com/source/app/blob/main/src/docker-compose.yml",
            "https://github.com/source/app/blob/main/src/app.csproj",
            "https://github.com/source/app/blob/main/src/infra/main.bicep",
        ], result["sourceFiles"])

    def test_ignores_tests_and_files_outside_requested_tree(self):
        result = scan(SOURCE, archive({
            "src/Program.cs": "WebApplication.CreateBuilder(args);",
            "src/Tests/TestServer.cs": "WebApplication.CreateBuilder(args);",
            "other/Program.cs": "WebApplication.CreateBuilder(args);",
        }))

        self.assertEqual(["https://github.com/source/app/blob/main/src/Program.cs"], result["sourceFiles"])

    def test_reports_oversized_candidate(self):
        result = scan(SOURCE, archive({
            "src/Program.cs": "WebApplication.CreateBuilder(args);" + "x" * (512 * 1024),
        }))

        self.assertEqual([], result["sourceFiles"])
        self.assertEqual([{"path": "src/Program.cs", "reason": "file_too_large"}], result["excludedFiles"])


if __name__ == "__main__":
    unittest.main()
