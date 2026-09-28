import base64
import io
import json
import unittest
import urllib.error
from unittest.mock import patch

from github_pr import GitHubClient, PublicationError, parse_request, publish


SCHEMA = {"database": {"name": "app", "engine": None}, "tables": [{"name": "orders"}], "types": []}


def payload():
    return {
        "repository": "target/catalogue",
        "schemas": [{
            "sourceUrl": "https://github.com/source/app/tree/main/src/Data",
            "schema": SCHEMA,
            "targetPath": "app/db-schema/database.schema.json",
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
    def test_parse_requires_json_object(self):
        with self.assertRaisesRegex(PublicationError, "one JSON object"):
            parse_request("[]")

    def test_rejects_invalid_schema(self):
        request = payload()
        request["schemas"][0]["schema"] = {"tables": []}
        with self.assertRaisesRegex(PublicationError, "database, tables, and types"):
            publish(request, FakeClient())

    def test_creates_one_commit_and_pull_request(self):
        client = FakeClient()
        result = publish(payload(), client, branch_factory=lambda: "dbschema/test")
        self.assertEqual("created", result["status"])
        self.assertEqual(7, result["pullRequestNumber"])
        self.assertEqual("app/db-schema/database.schema.json", result["filesWritten"][0]["path"])
        self.assertEqual(1, len([call for call in client.calls if call[1].endswith("/pulls")]))

    def test_unchanged_content_does_not_create_pull_request(self):
        existing = (json.dumps(SCHEMA, indent=2) + "\n").encode("utf-8")
        client = FakeClient(existing)
        result = publish(payload(), client)
        self.assertEqual("unchanged", result["status"])
        self.assertFalse(any(call[1].endswith("/pulls") for call in client.calls))

    def test_schema_and_manifest_share_one_tree(self):
        request = payload()
        request["manifestFile"] = {"path": "manifest.json", "content": []}
        client = FakeClient()
        result = publish(request, client, branch_factory=lambda: "dbschema/manifest")
        self.assertEqual(2, len(result["filesWritten"]))
        tree_call = next(call for call in client.calls if call[1].endswith("/git/trees"))
        self.assertEqual(2, len(tree_call[2]["tree"]))


class _Response(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def _http_error(code):
    return urllib.error.HTTPError("https://api.github.com/x", code, "error", {}, io.BytesIO(b'{"message": "boom"}'))


class GitHubClientTests(unittest.TestCase):
    def client(self):
        return GitHubClient("token", max_attempts=3, retry_delay_seconds=0)

    def test_read_timeout_is_retried_then_succeeds(self):
        outcomes = [TimeoutError("The read operation timed out"), _Response(b'{"sha": "blob-sha"}')]
        with patch("urllib.request.urlopen", side_effect=outcomes) as urlopen:
            result = self.client().request("POST", "/repos/target/catalogue/git/blobs", {"content": ""})
        self.assertEqual({"sha": "blob-sha"}, result)
        self.assertEqual(2, urlopen.call_count)

    def test_persistent_connection_failure_reports_github_unavailable_with_its_type(self):
        with patch("urllib.request.urlopen", side_effect=ConnectionResetError()) as urlopen:
            with self.assertRaises(PublicationError) as raised:
                self.client().request("GET", "/repos/target/catalogue")
        self.assertEqual("github_unavailable", raised.exception.code)
        self.assertIn("ConnectionResetError", str(raised.exception))
        self.assertEqual(3, urlopen.call_count)

    def test_server_error_is_retried(self):
        outcomes = [_http_error(502), _Response(b'{"sha": "tree-sha"}')]
        with patch("urllib.request.urlopen", side_effect=outcomes) as urlopen:
            result = self.client().request("POST", "/repos/target/catalogue/git/trees", {"tree": []})
        self.assertEqual({"sha": "tree-sha"}, result)
        self.assertEqual(2, urlopen.call_count)

    def test_pull_request_creation_is_never_retried(self):
        with patch("urllib.request.urlopen", side_effect=TimeoutError()) as urlopen:
            with self.assertRaises(PublicationError):
                self.client().request("POST", "/repos/target/catalogue/pulls", {"title": "t"})
        self.assertEqual(1, urlopen.call_count)

    def test_client_errors_are_not_retried(self):
        with patch("urllib.request.urlopen", side_effect=_http_error(404)) as urlopen:
            with self.assertRaisesRegex(PublicationError, "HTTP 404. boom"):
                self.client().request("GET", "/repos/target/catalogue/contents/x.json")
        self.assertEqual(1, urlopen.call_count)


if __name__ == "__main__":
    unittest.main()
