"""Responses host for c4 workflow orchestration."""

from __future__ import annotations

import asyncio
import json
import logging
import os

from azure.ai.agentserver.responses import CreateResponse, ResponseContext, ResponseEventStream, ResponsesAgentServerHost
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential

from workflow import WorkflowError, parse_workflow_request, run_workflow


logger = logging.getLogger(__name__)
PROJECT_ENDPOINT = os.getenv("FOUNDRY_PROJECT_ENDPOINT") or os.getenv("AZURE_AI_PROJECT_ENDPOINT")
MODEL = os.getenv("AZURE_AI_MODEL_DEPLOYMENT_NAME", "gpt-4o")
DISCOVERY_NAME = os.getenv("C4_DISCOVERY_AGENT_NAME", "c4-source-discovery")
GENERATOR_NAME = os.getenv("C4_GENERATOR_AGENT_NAME", "c4-generator")
PUBLISHER_NAME = os.getenv("C4_PR_CREATOR_AGENT_NAME", "c4-pr-creator")
MAX_FILES = int(os.getenv("C4_DISCOVERY_MAX_FILES", "150"))
BATCH_SIZE = int(os.getenv("C4_GENERATOR_BATCH_SIZE", "150"))
if not PROJECT_ENDPOINT:
    raise EnvironmentError("FOUNDRY_PROJECT_ENDPOINT is required.")

project_client = AIProjectClient(endpoint=PROJECT_ENDPOINT, credential=DefaultAzureCredential())
app = ResponsesAgentServerHost()


@app.response_handler
async def handle_create(request: CreateResponse, context: ResponseContext, cancellation_signal: asyncio.Event):
    stream = ResponseEventStream(response_id=context.response_id, request=request)
    yield stream.emit_created()
    yield stream.emit_in_progress()
    message = stream.add_output_item_message()
    yield message.emit_added()
    text = message.add_text_content()
    yield text.emit_added()
    try:
        payload = parse_workflow_request(await context.get_input_text() or "")
        result = await asyncio.to_thread(
            run_workflow, project_client, payload, DISCOVERY_NAME, GENERATOR_NAME, PUBLISHER_NAME, MODEL, MAX_FILES, BATCH_SIZE
        )
    except Exception as error:
        logger.exception("C4 workflow failed.")
        result = {
            "success": False,
            "sourceUrl": "",
            "generatedCatalogCount": 0,
            "discoveredFileCount": 0,
            "excludedFileCount": 0,
            "generationErrors": [{"errorType": type(error).__name__, "message": str(error)[:300]}],
            "catalogs": [],
            "pullRequest": None,
            "errors": [{"code": getattr(error, "code", "workflow_failed"), "message": str(error)[:300]}],
        }
    yield text.emit_delta(json.dumps(result, separators=(",", ":")))
    yield text.emit_text_done()
    yield text.emit_done()
    yield message.emit_done()
    yield stream.emit_completed()


if __name__ == "__main__":
    app.run()
