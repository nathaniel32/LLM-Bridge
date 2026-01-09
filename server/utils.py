from common.models import ResponseModel, MessageModel
from fastapi import WebSocket
from typing import List, Optional
import logging

async def ws_response(
    websockets: List[WebSocket],
    action,
    message: Optional[MessageModel] = None,
    content = None
) -> dict:
    response = ResponseModel(action=action, message=message, content=content)
    for websocket in websockets:
        try:
            await websocket.send_json(response.model_dump())
        except Exception as e:
            logging.error(f"Error sending to websocket: {e}")