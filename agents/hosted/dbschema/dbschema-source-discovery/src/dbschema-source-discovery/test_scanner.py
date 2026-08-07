import io
import unittest
import zipfile

from scanner import scan


SOURCE = "https://github.com/source/catalog/tree/main/src/Database"


def archive(files):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as output:
        for path, content in files.items():
            output.writestr(f"catalog-main/{path}", content)
    return buffer.getvalue()


class ScanTests(unittest.TestCase):
    def test_selects_authoritative_sources_and_reports_oversized_files(self):
        result = scan(SOURCE, archive({
            "src/Database/Migrations/2020_CreateOrders.cs": "migrationBuilder.CreateTable(name: \"Orders\");",
            "src/Database/AppDbContext.cs": "class AppDbContext : DbContext {}",
            "src/Database/Tables/Order.cs": "class Order { public int Id { get; set; } }",
            "src/Database/large.sql": "x" * (512 * 1024 + 1),
            "src/Database/AdhocScripts/Manual/backfill.sql": "CREATE TABLE ignored (id int);",
        }))

        self.assertEqual(3, len(result["schemaFiles"]))
        self.assertTrue(result["schemaFiles"][0].endswith("Migrations/2020_CreateOrders.cs"))
        self.assertEqual(
            [{"path": "src/Database/large.sql", "reason": "file_too_large"}],
            result["excludedFiles"],
        )

    def test_never_selects_files_outside_the_requested_tree(self):
        result = scan(SOURCE, archive({
            "src/Database/Tables/Order.cs": "class Order {}",
            "src/Other/Migrations/CreateOutside.cs": "migrationBuilder.CreateTable(name: \"Outside\");",
        }))

        self.assertEqual(
            ["https://github.com/source/catalog/blob/main/src/Database/Tables/Order.cs"],
            result["schemaFiles"],
        )
