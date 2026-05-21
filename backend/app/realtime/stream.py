import asyncio
import json
import logging
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ws", tags=["Realtime"])


@router.websocket("/scans/{scan_id}/stream")
async def scan_progress_stream(websocket: WebSocket, scan_id: str)-> Any:
    """
    WebSocket endpoint for real-time Phase 1 scan progress.
    The React frontend connects to this to update the UI loading bar.
    """

    await websocket.accept()

    try:
        #Redis Logic would be added here, but I'm going to mock all this for now

        mock_events = [
                {"progress": 10, "status": "running", "message": "Gathering DNS records..."}, #noqa: E501
                {"progress": 35, "status": "running", "message": "Querying Certificate Transparency logs (crt.sh)..."}, # noqa: E501
                {"progress": 60, "status": "running", "message": "Analyzing infrastructure via Shodan..."}, # noqa: E501
                {"progress": 85, "status": "running", "message": "Checking credential exposures (HaveIBeenPwned)..."}, #noqa: E501
                {"progress": 100, "status": "completed", "message": "Scan complete. Generating report..."} # noqa: E501
        ]

        for event in mock_events:
            await websocket.send_text(json.dumps({
                "scan_id": scan_id,
                **event
            }))
            await asyncio.sleep(2)

        await websocket.close()

    except WebSocketDisconnect:
        logger.info("Client disconnected from scan stream")