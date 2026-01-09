from websockets.client import ClientProtocol
from common.models import ResponseModel, MessageModel
from typing import Optional
import logging

async def ws_response(
    websocket: ClientProtocol,
    action,
    message:Optional[MessageModel] = None,
    content = None
) -> dict:
    response = ResponseModel(action=action, message=message, content=content)
    try:
        await websocket.send(response.model_dump_json())
    except Exception as e:
        logging.error(f"Error sending to websocket: {e}")