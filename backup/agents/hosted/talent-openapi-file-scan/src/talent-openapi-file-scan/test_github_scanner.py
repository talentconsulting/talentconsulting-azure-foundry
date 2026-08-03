import unittest

from github_scanner import (
    Endpoint,
    SourceFile,
    attach_payload_files,
    discover_action_type_names,
    discover_aspnet_endpoints,
    is_infrastructure_controller,
    parse_source_url,
    scan_source_url,
    scan_inventory,
)


class SourceUrlTests(unittest.TestCase):
    def test_parses_repository_ref_and_path(self):
        location = parse_source_url(
            "https://github.com/talentconsulting/talentsuite-bidmanager/"
            "tree/main/src/TalentSuite.Server"
        )
        self.assertEqual(location.repository_ref, "talentconsulting/talentsuite-bidmanager")
        self.assertEqual(location.ref, "main")
        self.assertEqual(location.base_path, "src/TalentSuite.Server")


class AspNetEndpointTests(unittest.TestCase):
    def test_discovers_every_http_attribute(self):
        source = """
        [ApiController]
        [Route("api/[controller]")]
        public class BidsController : ControllerBase
        {
            [HttpGet]
            public IActionResult List() => Ok();
            [HttpGet("{id:guid}")]
            public IActionResult Get(Guid id) => Ok();
            [HttpPost]
            public IActionResult Create(CreateBidRequest request) => Ok();
            [HttpPatch("{id:guid}/status")]
            public IActionResult UpdateStatus(Guid id) => Ok();
        }
        """
        actual = {
            (item.method, item.path) for item in discover_aspnet_endpoints(source)
        }
        self.assertEqual(
            actual,
            {
                ("get", "/api/bids"),
                ("get", "/api/bids/{id}"),
                ("post", "/api/bids"),
                ("patch", "/api/bids/{id}/status"),
            },
        )

    def test_identifies_health_controller_as_infrastructure(self):
        source = SourceFile(
            "src/Health/HealthController.cs",
            "",
            (Endpoint("get", "/health", "Get"),),
        )
        self.assertTrue(is_infrastructure_controller(source))

    def test_discovers_request_and_response_types_from_actions(self):
        source = """
        [HttpPost]
        [ProducesResponseType(typeof(BidResponse), 201)]
        public async Task<ActionResult<BidResponse>> Create(
            [FromBody] CreateBidRequest request, CancellationToken cancellationToken)
        { return Ok(); }
        """
        names = discover_action_type_names(source)
        self.assertIn("CreateBidRequest", names)
        self.assertIn("BidResponse", names)

    def test_attaches_payload_files_and_nested_model_dependencies(self):
        controller = SourceFile(
            "src/Controllers/BidsController.cs",
            """
            [HttpPost]
            public ActionResult<BidResponse> Create(CreateBidRequest request) => Ok();
            """,
            (Endpoint("post", "/api/bids", "Create"),),
        )
        sources = {
            controller.path: controller.content,
            "src/Contracts/CreateBidRequest.cs": (
                "public record CreateBidRequest(Money Budget);"
            ),
            "src/Contracts/BidResponse.cs": (
                "public sealed record class BidResponse(Guid Id);"
            ),
            "src/Contracts/Money.cs": "public record Money(decimal Amount);",
            "src/Services/BidService.cs": "public class BidService {}",
        }

        actual = attach_payload_files(controller, sources)

        self.assertEqual(
            dict(actual.payload_files),
            {
                "src/Contracts/BidResponse.cs": ("BidResponse",),
                "src/Contracts/CreateBidRequest.cs": ("CreateBidRequest",),
                "src/Contracts/Money.cs": ("Money",),
            },
        )

    def test_tree_scan_adds_payload_sources_without_generating_specs_for_them(self):
        class FakeGitHubClient:
            def archive_sources(self, _location):
                return [
                    (
                        "src/Controllers/BidsController.cs",
                        """
                        [Route("api/[controller]")]
                        public class BidsController : ControllerBase {
                            [HttpPost]
                            public ActionResult<BidResponse> Create(
                                CreateBidRequest request) => Ok();
                        }
                        """,
                    ),
                    (
                        "src/Contracts/CreateBidRequest.cs",
                        "public record CreateBidRequest(string Title);",
                    ),
                    (
                        "src/Contracts/BidResponse.cs",
                        "public record BidResponse(Guid Id);",
                    ),
                ]

        actual = scan_source_url(
            "https://github.com/example/repository/tree/main/src/Controllers",
            client=FakeGitHubClient(),
        )

        self.assertEqual(len(actual), 1)
        self.assertEqual(actual[0].path, "src/Controllers/BidsController.cs")
        self.assertEqual(
            dict(actual[0].payload_files),
            {
                "src/Contracts/BidResponse.cs": ("BidResponse",),
                "src/Contracts/CreateBidRequest.cs": ("CreateBidRequest",),
            },
        )

        inventory = scan_inventory(
            "https://github.com/example/repository/tree/main/src/Controllers",
            client=FakeGitHubClient(),
        )
        self.assertEqual(
            inventory["apiFiles"][0],
            {
                "apiFilePath": "src/Controllers/BidsController.cs",
                "payloadFiles": {
                    "src/Contracts/BidResponse.cs": ["BidResponse"],
                    "src/Contracts/CreateBidRequest.cs": ["CreateBidRequest"],
                },
            },
        )


if __name__ == "__main__":
    unittest.main()
