"""Hosted scanner-to-generator workflow exposed through Responses protocol."""

from __future__ import annotations

import asyncio
import json
import logging
import os

from azure.ai.agentserver.responses import (
    CreateResponse,
    ResponseContext,
    ResponseEventStream,
    ResponsesAgentServerHost,
)
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential

from workflow import WorkflowInputError, run_workflow


logger = logging.getLogger(__name__)
PROJECT_ENDPOINT = os.getenv("FOUNDRY_PROJECT_ENDPOINT") or os.getenv(
    "AZURE_AI_PROJECT_ENDPOINT"
)
FILE_SCAN_NAME = os.getenv("OPENAPI_FILE_SCAN_AGENT_NAME", "talent-openapi-file-scan")
GENERATOR_NAME = os.getenv("OPENAPI_GENERATOR_AGENT_NAME", "openapi-spec-generator")
FILE_SCAN_MODEL = os.getenv("OPENAPI_FILE_SCAN_MODEL", FILE_SCAN_NAME)
GENERATOR_MODEL = os.getenv("OPENAPI_GENERATOR_MODEL", "gpt-4o")
MAX_CONCURRENCY = int(os.getenv("OPENAPI_MAX_CONCURRENCY", "4"))
MAX_FILES = int(os.getenv("OPENAPI_MAX_FILES", "100"))
if not PROJECT_ENDPOINT:
    raise EnvironmentError("FOUNDRY_PROJECT_ENDPOINT is required.")

project_client = AIProjectClient(
    endpoint=PROJECT_ENDPOINT,
    credential=DefaultAzureCredential(),
    allow_preview=True,
)
app = ResponsesAgentServerHost()


def extract_source_directory_url(user_input: str) -> str:
    value = user_input.strip()
    try:
        payload = json.loads(value)
    except json.JSONDecodeError:
        payload = None
    if isinstance(payload, dict) and isinstance(
        payload.get("sourceDirectoryUrl"), str
    ):
        return payload["sourceDirectoryUrl"]
    if value.startswith("https://github.com/"):
        return value
    raise WorkflowInputError(
        'Input must be JSON containing a "sourceDirectoryUrl" string.'
    )


@app.response_handler
async def handle_create(
    request: CreateResponse,
    context: ResponseContext,
    cancellation_signal: asyncio.Event,
):
    stream = ResponseEventStream(response_id=context.response_id, request=request)
    yield stream.emit_created()
    yield stream.emit_in_progress()
    message = stream.add_output_item_message()
    yield message.emit_added()
    text = message.add_text_content()
    yield text.emit_added()

    source_directory_url = ""
    try:
        source_directory_url = extract_source_directory_url(
            await context.get_input_text() or ""
        )
        result = await asyncio.to_thread(
            run_workflow,
            project_client,
            source_directory_url,
            FILE_SCAN_NAME,
            FILE_SCAN_MODEL,
            GENERATOR_NAME,
            GENERATOR_MODEL,
            MAX_CONCURRENCY,
            MAX_FILES,
        )
    except Exception as error:
        logger.exception("Hosted OpenAPI workflow failed.")
        result = {
            "success": False,
            "sourceDirectoryUrl": source_directory_url,
            "apiFiles": [],
            "specs": [],
            "errors": [
                {
                    "sourceFileUrl": "",
                    "errorType": type(error).__name__,
                }
            ],
        }

    yield text.emit_delta(json.dumps(result, separators=(",", ":")))
    yield text.emit_text_done()
    yield text.emit_done()
    yield message.emit_done()
    yield stream.emit_completed()


if __name__ == "__main__":
    app.run()
