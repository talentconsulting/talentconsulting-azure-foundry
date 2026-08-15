import base64
import json
import unittest

from github_pr import PublicationError, parse_request, publish


DRAWIO = '<mxfile><diagram name="Context"><mxGraphModel><root /></mxGraphModel></diagram></mxfile>'
CATALOG = {
    "repository": "source/app",
    "ref": "main",
    "path": "src",
    "c4Model": {
        "systemName": "Application",
        "description": "Application under analysis.",
        "people": [],
        "systems": [{"id": "application", "name": "Application", "description": "System under analysis.", "external": False, "evidence": []}],
        "containers": [],
        "relationships": [],
        "evidence": [],
    },
    "diagrams": {
        "context": {"format": "drawio", "filename": "context.drawio", "drawioXml": DRAWIO},
        "container": {"format": "drawio", "filename": "container.drawio", "drawioXml": DRAWIO},
    },
}


def payload():
    return {
        "repository": "target/catalogue",
        "catalogs": [{
            "sourceUrl": "https://github.com/source/app/tree/main/src",
            "catalog": CATALOG,
            "targetDirectory": "app/c4",
        }],
    }


class FakeClient:
    def __init__(self, existing=None):
        self.existing = existing
        self.calls = []

    def request(self, method, path, body=None):
        self.calls.append((method, path, body))
        if method == "GET" and path == "/repos/target/catalogue":
            return {"default_branch": "main"}
        if method == "GET" and "/contents/" in path:
            if self.existing is None:
                raise PublicationError("github_api_error", "GitHub API returned HTTP 404. Not Found")
            return {"type": "file", "content": base64.b64encode(self.existing).decode("ascii")}
        if method == "GET" and "/git/ref/heads/" in path:
            return {"object": {"sha": "base-sha"}}
        if method == "GET" and "/git/commits/base-sha" in path:
            return {"tree": {"sha": "base-tree"}}
        if method == "POST" and path.endswith("/git/blobs"):
            return {"sha": "blob-sha"}
        if method == "POST" and path.endswith("/git/trees"):
            return {"sha": "tree-sha"}
        if method == "POST" and path.endswith("/git/commits"):
            return {"sha": "commit-sha"}
        if method == "POST" and path.endswith("/git/refs"):
            return {}
        if method == "POST" and path.endswith("/pulls"):
            return {"html_url": "https://github.com/target/catalogue/pull/7", "number": 7}
        raise AssertionError((method, path, body))


class PublisherTests(unittest.TestCase):
    def test_rejects_invalid_catalog(self):
        request = payload()
        request["catalogs"][0]["catalog"] = {"diagrams": {}}
        with self.assertRaisesRegex(PublicationError, "repository, ref, path"):
            publish(request, FakeClient())

    def test_creates_json_and_drawio_files_in_one_pull_request(self):
        client = FakeClient()
        result = publish(payload(), client, branch_factory=lambda: "c4/test")
        self.assertEqual("created", result["status"])
        self.assertEqual(["app/c4/c4.json", "app/c4/context.drawio", "app/c4/container.drawio"], [
            item["path"] for item in result["filesWritten"]
        ])
        self.assertEqual(1, len([call for call in client.calls if call[1].endswith("/pulls")]))

    def test_unchanged_content_does_not_create_pull_request(self):
        client = FakeClient((json.dumps(CATALOG, indent=2) + "\n").encode("utf-8"))
        result = publish(payload(), client)
        self.assertEqual("created", result["status"])
        self.assertTrue(any(call[1].endswith("/pulls") for call in client.calls))

    def test_catalog_and_manifest_share_one_tree(self):
        request = payload()
        request["manifestFile"] = {"path": "manifest.json", "content": []}
        result = publish(request, FakeClient(), branch_factory=lambda: "c4/manifest")
        self.assertEqual(4, len(result["filesWritten"]))

    def test_parse_requires_json_object(self):
        with self.assertRaisesRegex(PublicationError, "one JSON object"):
            parse_request("[]")


if __name__ == "__main__":
    unittest.main()
