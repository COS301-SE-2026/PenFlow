import json
from unittest.mock import AsyncMock, patch

import pytest

from app.realtime.stream import scan_progress_stream


@pytest.mark.asyncio
@patch("app.realtime.stream.asyncio.sleep",new_callable= AsyncMock)
#test websocket connection handling ,test scan_progress_stream sends progress update via websocket 
async def test_scan_progress_stream_send__all_mock_events_and_closes(mock_sleep) :
    websocket = AsyncMock()
    scan_id = "test-scan-id"

    await scan_progress_stream(websocket, scan_id)

    websocket.accept.assert_awaited_once()
    websocket.close.assert_awaited_once()
    assert websocket.send_text.await_count == 5
    assert mock_sleep.await_count ==5

    sent_payloads = [
                json.loads(call.args[0]) for call in websocket.send_text.await_args_list
    ]

    assert all(payload["scan id"] == scan_id for payload in sent_payloads)
    assert [p["progress"] for p in sent_payloads]  == [ 10, 35, 60, 85, 100]
    assert sent_payloads[0] ["status"] == "running"
    assert sent_payloads[-1]["status"]
 
