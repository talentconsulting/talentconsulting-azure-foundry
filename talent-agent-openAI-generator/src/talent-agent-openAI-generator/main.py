"""Hosted OpenAPI generator with deterministic GitHub traversal."""

from __future__ import annotations

import asyncio
import json
import logging
import os
from typing import Any

from azure.ai.agentserver.responses import (
    CreateResponse,
    ResponseContext,
    ResponseEventStream,
    ResponsesAgentServerHost,
)
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential

from github_scanner import ScanError, SourceFile, scan_source_url
from spec_generator import fallback_document, parse_json_object, wrap_spec


logger = logging.getLogger(__name__)
PROJECT_ENDPOINT = os.getenv("FOUNDRY_PROJECT_ENDPOINT")
MODEL_NAME = os.getenv("AZURE_AI_MODEL_DEPLOYMENT_NAME") or os.getenv("FOUNDRY_MODEL_NAME")
if not PROJECT_ENDPOINT:
    raise EnvironmentError("FOUNDRY_PROJECT_ENDPOINT is required.")
if not MODEL_NAME:
    raise EnvironmentError("AZURE_AI_MODEL_DEPLOYMENT_NAME is required.")

_project_client = AIProjectClient(
    endpoint=PROJECT_ENDPOINT,
    credential=DefaultAzureCredential(),
)
_openai_client = _project_client.get_openai_client()
app = ResponsesAgentServerHost()


def _extract_source_url(user_input: str) -> str:
    value = user_input.strip()
    try:
        payload = json.loads(value)
    except json.JSONDecodeError:
        payload = None
    if isinstance(payload, dict) and isinstance(payload.get("sourceUrl"), str):
        return payload["sourceUrl"]
    if value.startswith("https://github.com/"):
        return value
    raise ScanError('Input must be JSON with a non-empty "sourceUrl" string.')


def _model_document(source: SourceFile) -> dict[str, Any]:
    ledger = [
        {
            "method": endpoint.method.upper(),
            "path": endpoint.path,
            "operationName": endpoint.operation_name,
        }
        for endpoint in source.endpoints
    ]
    prompt = {
        "task": (
            "Generate one complete OpenAPI 3.1 JSON document for this ASP.NET "
            "controller. Include every endpointLedger entry. Return JSON only."
        ),
        "sourcePath": source.path,
        "endpointLedger": ledger,
        "source": source.content,
    }
    try:
        response = _openai_client.responses.create(
            model=MODEL_NAME,
            instructions=(
                "Convert one already-enumerated API source file into OpenAPI 3.1. "
                "Never omit an endpointLedger method/path. Return JSON only."
            ),
            input=json.dumps(prompt, separators=(",", ":")),
        )
        return parse_json_object(response.output_text)
    except Exception:
        logger.exception("Model generation failed for %s; using fallback.", source.path)
        return fallback_document(source)


def generate(source_url: str) -> dict[str, Any]:
    sources = scan_source_url(source_url)
    specs = [wrap_spec(source, _model_document(source)) for source in sources]
    scanned_files = [source.path for source in sources]
    if len(specs) != len(scanned_files):
        raise RuntimeError("Specification count does not match source-file census.")
    return {"scannedFiles": scanned_files, "specs": specs}


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

    try:
        source_url = _extract_source_url(await context.get_input_text() or "")
        result = await asyncio.to_thread(generate, source_url)
    except Exception as error:
        logger.exception("OpenAPI generation failed.")
        result = {"scannedFiles": [], "specs": []}

    yield text.emit_delta(json.dumps(result, separators=(",", ":")))
    yield text.emit_text_done()
    yield text.emit_done()
    yield message.emit_done()
    yield stream.emit_completed()


if __name__ == "__main__":
    app.run()
