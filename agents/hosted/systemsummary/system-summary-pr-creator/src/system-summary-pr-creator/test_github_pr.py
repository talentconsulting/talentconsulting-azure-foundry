import json
import unittest

from github_pr import PublicationError, parse_request, publish


CONTENT = {"systems": [{"repository": "source/app", "name": "App"}]}


def payload():
    return {"repository": "org/catalogue", "targetPath": "system-summaries.json", "fileContent": CONTENT}


class FakeClient:
    def __init__(self, existing=None):
        self.existing = existing
        self.calls = []

    def request(self, method, path, body=None):
        self.calls.append((method, path, body))
        if method == "GET" and path == "/repos/org/catalogue":
            return {"default_branch": "main"}
        if method == "GET" and "/contents/" in path:
            if self.existing is None:
                raise PublicationError("github_api_error", "GitHub API returned HTTP 404. Not Found")
            import base64
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
            return {"html_url": "https://github.com/org/catalogue/pull/9", "number": 9}
        raise AssertionError((method, path, body))


class PublisherTests(unittest.TestCase):
    def test_parse_requires_json_object(self):
        with self.assertRaisesRegex(PublicationError, "one JSON object"):
            parse_request("[]")

    def test_rejects_a_non_json_target_path(self):
        request = payload()
        request["targetPath"] = "system-summaries.txt"
        with self.assertRaisesRegex(PublicationError, "\\.json"):
            publish(request, FakeClient())

    def test_publish_accepts_the_output_of_parse_request(self):
        # main.py always calls publish(parse_request(text)); parse_request must return the
        # original payload, not validate_request's transformed shape, or this double-call fails.
        client = FakeClient()
        result = publish(parse_request(json.dumps(payload())), client, branch_factory=lambda: "system-summary/test")
        self.assertEqual("created", result["status"])

    def test_creates_one_commit_and_pull_request(self):
        client = FakeClient()
        result = publish(payload(), client, branch_factory=lambda: "system-summary/test")
        self.assertEqual("created", result["status"])
        self.assertEqual(9, result["pullRequestNumber"])
        self.assertEqual("system-summaries.json", result["filesWritten"][0]["path"])
        self.assertEqual(1, len([call for call in client.calls if call[1].endswith("/pulls")]))

    def test_unchanged_content_does_not_create_pull_request(self):
        existing = (json.dumps(CONTENT, indent=2) + "\n").encode("utf-8")
        client = FakeClient(existing)
        result = publish(payload(), client)
        self.assertEqual("unchanged", result["status"])
        self.assertFalse(any(call[1].endswith("/pulls") for call in client.calls))


if __name__ == "__main__":
    unittest.main()
