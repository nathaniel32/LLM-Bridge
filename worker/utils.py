from websockets.client import ClientProtocol
from common.models import ResponseModel, MessageModel

async def ws_response(
    websocket: ClientProtocol,
    action,
    message=None,
    message_status=None,
    content=None
) -> dict:
    message_model = None if message is None else MessageModel(text=message, status=message_status)
    response = ResponseModel(action=action, message=message_model, content=content)
    try:
        await websocket.send(response.model_dump_json())
    except Exception as e:
        print(f"Error sending to websocket: {e}")