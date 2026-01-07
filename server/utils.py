from common.models import ResponseModel
from fastapi import WebSocket
from typing import List

async def ws_response(
    websockets: List[WebSocket],
    action,
    message=None,
    status_type=None,
    content=None
) -> dict:
    response = ResponseModel(action=action, message=message, status_type=status_type, content=content)
    #print(response.content)
    for websocket in websockets:
        try:
            await websocket.send_json(response.model_dump())
        except Exception as e:
            print(f"Error sending to websocket: {e}")