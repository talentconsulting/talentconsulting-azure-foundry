"""Responses-protocol host for the OpenAPI Source Discovery scanner."""

from __future__ import annotations

import asyncio
import json
import logging

from azure.ai.agentserver.responses import (
    CreateResponse,
    ResponseContext,
    ResponseEventStream,
    ResponsesAgentServerHost,
)

from scanner import ScanError, scan


logger = logging.getLogger(__name__)
app = ResponsesAgentServerHost()


def extract_source_url(user_input: str) -> str:
    try:
        payload = json.loads(user_input.strip())
    except json.JSONDecodeError as error:
        raise ScanError("Input must be valid JSON.") from error
    if (
        not isinstance(payload, dict)
        or set(payload) != {"sourceUrl"}
        or not isinstance(payload["sourceUrl"], str)
        or not payload["sourceUrl"].strip()
    ):
        raise ScanError('Input must contain exactly one non-empty "sourceUrl" property.')
    return payload["sourceUrl"].strip()


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
        source_url = extract_source_url(await context.get_input_text() or "")
        result = await asyncio.to_thread(scan, source_url)
    except Exception:
        logger.exception("OpenAPI Source Discovery scan failed.")
        result = []

    yield text.emit_delta(json.dumps(result, separators=(",", ":")))
    yield text.emit_text_done()
    yield text.emit_done()
    yield message.emit_done()
    yield stream.emit_completed()


if __name__ == "__main__":
    app.run()
