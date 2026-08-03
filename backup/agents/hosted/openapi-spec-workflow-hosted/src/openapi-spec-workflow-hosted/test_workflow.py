import json
import unittest
from types import SimpleNamespace

from workflow import invoke_agent, run_workflow


SOURCE_DIRECTORY = (
    "https://github.com/example/api/tree/main/src/Controllers"
)
FILE_A = "https://github.com/example/api/blob/main/src/Controllers/AController.cs"
FILE_B = "https://github.com/example/api/blob/main/src/Controllers/BController.cs"
SCAN_OUTPUT = {
    "apiFiles": [
        {
            "apiFilePath": "src/Controllers/AController.cs",
            "payloadFiles": {
                "src/Contracts/ARequest.cs": ["ARequest"]
            },
        },
        {
            "apiFilePath": "src/Controllers/BController.cs",
            "payloadFiles": {},
        },
    ]
}


class FakeResponses:
    def __init__(self, handler):
        self.handler = handler

    def create(self, model, input, timeout):
        return SimpleNamespace(output_text=json.dumps(self.handler(json.loads(input))))


class FakeClient:
    def __init__(self, handler):
        self.responses = FakeResponses(handler)


class FakeProject:
    generated_inputs = []

    def get_openai_client(self, agent_name):
        if agent_name == "scanner":
            return FakeClient(lambda _: SCAN_OUTPUT)

        def generate(payload):
            self.generated_inputs.append(payload)
            path = payload["sourceFileUrl"].split("/blob/main/", 1)[1]
            stem = path.rsplit("/", 1)[-1].removesuffix("Controller.cs").lower()
            return {
                "domainApi": stem,
                "openapi": {
                    "openapi": "3.1.0",
                    "info": {"title": stem, "version": "1.0.0"},
                    "paths": {f"/{stem}": {"get": {"responses": {"200": {}}}}},
                },
                "serviceName": stem,
                "sourcePath": path,
                "fileName": f"{stem}.json",
                "contentType": "application/json",
            }

        return FakeClient(generate)


class WorkflowTests(unittest.TestCase):
    def test_scans_then_generates_one_spec_per_url_in_scanner_order(self):
        FakeProject.generated_inputs = []
        result = run_workflow(
            FakeProject(),
            SOURCE_DIRECTORY,
            "scanner",
            "gpt-4o",
            "generator",
            "gpt-4o",
            max_concurrency=2,
        )

        self.assertTrue(result["success"])
        self.assertEqual(result["apiFiles"], SCAN_OUTPUT["apiFiles"])
        self.assertEqual(
            [spec["sourcePath"] for spec in result["specs"]],
            [
                "src/Controllers/AController.cs",
                "src/Controllers/BController.cs",
            ],
        )
        generated_a = next(
            item for item in FakeProject.generated_inputs
            if item["sourceFileUrl"] == FILE_A
        )
        self.assertEqual(
            generated_a,
            {
                "sourceFileUrl": FILE_A,
                "payloadFiles": {
                    "src/Contracts/ARequest.cs": ["ARequest"]
                },
            },
        )
        self.assertEqual(result["errors"], [])

    def test_retries_one_malformed_prompt_response(self):
        calls = 0

        def handler(_):
            nonlocal calls
            calls += 1
            if calls == 1:
                return "not-json"
            return {"apiFiles": []}

        class RetryingResponses:
            def create(self, model, input, timeout):
                result = handler(json.loads(input))
                text = result if isinstance(result, str) else json.dumps(result)
                return SimpleNamespace(output_text=text)

        project = SimpleNamespace(
            get_openai_client=lambda agent_name: SimpleNamespace(
                responses=RetryingResponses()
            )
        )

        self.assertEqual(
            invoke_agent(project, "scanner", "gpt-4o", {}),
            {"apiFiles": []},
        )
        self.assertEqual(calls, 2)


if __name__ == "__main__":
    unittest.main()
