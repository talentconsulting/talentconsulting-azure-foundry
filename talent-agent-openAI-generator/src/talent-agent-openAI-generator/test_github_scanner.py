import unittest

from github_scanner import (
    Endpoint,
    SourceFile,
    discover_aspnet_endpoints,
    is_infrastructure_controller,
    parse_source_url,
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


if __name__ == "__main__":
    unittest.main()
