"""Hosted API and payload source-file scanner."""

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
from github_scanner import ScanError, scan_inventory


logger = logging.getLogger(__name__)
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
        result = await asyncio.to_thread(scan_inventory, source_url)
    except Exception:
        logger.exception("API source scan failed.")
        result = {"apiFiles": []}

    yield text.emit_delta(json.dumps(result, separators=(",", ":")))
    yield text.emit_text_done()
    yield text.emit_done()
    yield message.emit_done()
    yield stream.emit_completed()


if __name__ == "__main__":
    app.run()
