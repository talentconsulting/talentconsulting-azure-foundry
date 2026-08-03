import unittest

from scanner import ScanError, parse_source_url, scan


SOURCE_URL = "https://github.com/example/catalog/tree/feature-api/src/Api"


class SourceUrlTests(unittest.TestCase):
    def test_parses_full_repository_ref_and_path(self):
        location = parse_source_url(SOURCE_URL)
        self.assertEqual(location.owner, "example")
        self.assertEqual(location.repository, "catalog")
        self.assertEqual(location.ref, "feature-api")
        self.assertEqual(location.base_path, "src/Api")

    def test_rejects_non_tree_url(self):
        with self.assertRaises(ScanError):
            parse_source_url("https://github.com/example/catalog")


class ScanTests(unittest.TestCase):
    def test_returns_api_and_transitive_payload_files_as_blob_urls(self):
        sources = {
            "src/Api/Controllers/BidsController.cs": """
                [ApiController]
                public class BidsController : ControllerBase
                {
                    [HttpPost]
                    [ProducesResponseType(typeof(BidResponse), 201)]
                    public ActionResult<BidResponse> Create(
                        [FromBody] CreateBidRequest request) => Ok();
                }
            """,
            "src/Contracts/CreateBidRequest.cs": (
                "public record CreateBidRequest(Money Budget);"
            ),
            "src/Contracts/BidResponse.cs": (
                "public sealed record BidResponse(Guid Id);"
            ),
            "src/Contracts/Money.cs": "public record Money(decimal Amount);",
            "src/Services/BidService.cs": "public class BidService {}",
        }

        actual = scan(SOURCE_URL, sources=sources)

        self.assertEqual(
            actual,
            [
                {
                    "apiFile": (
                        "https://github.com/example/catalog/blob/feature-api/"
                        "src/Api/Controllers/BidsController.cs"
                    ),
                    "supportingFiles": [
                        "https://github.com/example/catalog/blob/feature-api/"
                        "src/Contracts/BidResponse.cs",
                        "https://github.com/example/catalog/blob/feature-api/"
                        "src/Contracts/CreateBidRequest.cs",
                        "https://github.com/example/catalog/blob/feature-api/"
                        "src/Contracts/Money.cs",
                    ],
                }
            ],
        )

    def test_does_not_return_api_files_outside_the_supplied_path(self):
        sources = {
            "src/Api/OrdersController.cs": (
                "[HttpGet] public class OrdersController {}"
            ),
            "src/Other/AdminController.cs": (
                "[HttpGet] public class AdminController {}"
            ),
        }

        actual = scan(SOURCE_URL, sources=sources)

        self.assertEqual(len(actual), 1)
        self.assertTrue(actual[0]["apiFile"].endswith("src/Api/OrdersController.cs"))


if __name__ == "__main__":
    unittest.main()
