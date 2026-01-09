from common.models import ResponseModel, MessageModel
from fastapi import WebSocket
from typing import List

async def ws_response(
    websockets: List[WebSocket],
    action,
    message=None,
    message_status=None,
    content=None
) -> dict:
    message_model = None if message is None else MessageModel(text=message, status=message_status)
    response = ResponseModel(action=action, message=message_model, content=content)
    print(message)
    for websocket in websockets:
        try:
            await websocket.send_json(response.model_dump())
        except Exception as e:
            print(f"Error sending to websocket: {e}")