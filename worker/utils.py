from websockets.client import ClientProtocol
from common.models import ResponseModel

async def ws_response(
    websocket: ClientProtocol,
    action,
    message=None,
    message_status=None,
    content=None
) -> dict:
    response = ResponseModel(action=action, message=message, message_status=message_status, content=content)
    try:
        await websocket.send(response.model_dump_json())
    except Exception as e:
        print(f"Error sending to websocket: {e}")