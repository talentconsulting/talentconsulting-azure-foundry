import json
import unittest

from workflow import WorkflowError, parse_workflow_request, run_workflow


SOURCE = "https://github.com/source/app/tree/main/src/Api"
API_1 = "https://github.com/source/app/blob/main/src/Api/BidsController.cs"
API_2 = "https://github.com/source/app/blob/main/src/Api/UsersController.cs"
DTO = "https://github.com/source/app/blob/main/src/Api/BidDto.cs"
SPEC = {
    "openapi": "3.1.0",
    "info": {"title": "API", "version": "1.0.0"},
    "paths": {},
    "components": {"schemas": {}},
}


class WorkflowTests(unittest.TestCase):
    def test_input_requires_destination_repository(self):
        with self.assertRaisesRegex(WorkflowError, "targetRepository"):
            parse_workflow_request(json.dumps({"sourceUrl": SOURCE}))

    def test_calls_generator_for_each_api_then_publisher_once(self):
        calls = []

        def invoke(project, name, model, payload, max_attempts=2):
            calls.append((name, payload))
            if name == "discovery":
                return [
                    {"apiFile": API_1, "supportingFiles": [DTO]},
                    {"apiFile": API_2, "supportingFiles": []},
                ]
            if name == "generator":
                return dict(SPEC)
            if name == "publisher":
                self.assertEqual(1, max_attempts)
                return {"success": True, "status": "created", "pullRequestUrl": "https://example/pull/1"}
            raise AssertionError(name)

        result = run_workflow(
            object(),
            {"sourceUrl": SOURCE, "targetRepository": "target/specs"},
            "discovery",
            "generator",
            "publisher",
            "gpt-4o",
            invoker=invoke,
        )
        self.assertTrue(result["success"])
        self.assertEqual(2, result["generatedCount"])
        generator_calls = [call for call in calls if call[0] == "generator"]
        publisher_calls = [call for call in calls if call[0] == "publisher"]
        self.assertEqual(2, len(generator_calls))
        self.assertEqual(1, len(publisher_calls))
        self.assertEqual("app/open-api", publisher_calls[0][1]["targetDirectory"])
        self.assertEqual([API_1, API_2], [item["apiFile"] for item in publisher_calls[0][1]["specifications"]])

    def test_explicit_target_directory_overrides_repository_layout(self):
        def invoke(project, name, model, payload, max_attempts=2):
            if name == "discovery":
                return [{"apiFile": API_1, "supportingFiles": []}]
            if name == "generator":
                return dict(SPEC)
            self.assertEqual("custom/specs", payload["targetDirectory"])
            return {"success": True, "status": "created"}

        result = run_workflow(
            object(),
            {
                "sourceUrl": SOURCE,
                "targetRepository": "target/specs",
                "targetDirectory": "custom/specs",
            },
            "discovery",
            "generator",
            "publisher",
            "gpt-4o",
            invoker=invoke,
        )

        self.assertTrue(result["success"])

    def test_partial_generation_publishes_successes_and_reports_failure(self):
        def invoke(project, name, model, payload, max_attempts=2):
            if name == "discovery":
                return [
                    {"apiFile": API_1, "supportingFiles": []},
                    {"apiFile": API_2, "supportingFiles": []},
                ]
            if name == "generator" and payload["apiFile"] == API_2:
                raise RuntimeError("generation failed")
            if name == "generator":
                return dict(SPEC)
            self.assertEqual(1, len(payload["specifications"]))
            return {"success": True, "status": "created"}

        result = run_workflow(
            object(),
            {"sourceUrl": SOURCE, "targetRepository": "target/specs"},
            "discovery",
            "generator",
            "publisher",
            "gpt-4o",
            invoker=invoke,
        )
        self.assertFalse(result["success"])
        self.assertEqual(1, result["generatedCount"])
        self.assertEqual(API_2, result["generationErrors"][0]["apiFile"])

    def test_empty_discovery_does_not_call_publisher(self):
        def invoke(project, name, model, payload, max_attempts=2):
            self.assertEqual("discovery", name)
            return []

        result = run_workflow(
            object(),
            {"sourceUrl": SOURCE, "targetRepository": "target/specs"},
            "discovery",
            "generator",
            "publisher",
            "gpt-4o",
            invoker=invoke,
        )
        self.assertEqual("no_api_files", result["errors"][0]["code"])

    def test_can_defer_publication_and_return_generated_specifications(self):
        calls = []

        def invoke(project, name, model, payload, max_attempts=2):
            calls.append(name)
            if name == "discovery":
                return [{"apiFile": API_1, "supportingFiles": []}]
            if name == "generator":
                return dict(SPEC)
            raise AssertionError("Publisher must not be called in deferred mode.")

        result = run_workflow(
            object(),
            {"sourceUrl": SOURCE, "deferPublication": True},
            "discovery",
            "generator",
            "publisher",
            "gpt-4o",
            invoker=invoke,
        )

        self.assertTrue(result["success"])
        self.assertEqual(["discovery", "generator"], calls)
        self.assertEqual(API_1, result["specifications"][0]["apiFile"])
        self.assertIsNone(result["pullRequest"])


if __name__ == "__main__":
    unittest.main()
