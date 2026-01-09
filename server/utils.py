from common.models import ResponseModel, MessageModel
from fastapi import WebSocket
from typing import List, Optional

async def ws_response(
    websockets: List[WebSocket],
    action,
    message: Optional[MessageModel] = None,
    content = None
) -> dict:
    response = ResponseModel(action=action, message=message, content=content)
    print(message)
    for websocket in websockets:
        try:
            await websocket.send_json(response.model_dump())
        except Exception as e:
            print(f"Error sending to websocket: {e}")