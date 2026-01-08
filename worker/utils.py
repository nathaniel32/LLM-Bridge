from websockets.client import ClientProtocol
from common.models import ResponseModel

async def ws_response(
    websocket: ClientProtocol,
    action,
    message=None,
    status_type=None,
    content=None
) -> dict:
    response = ResponseModel(action=action, message=message, status_type=status_type, content=content)
    try:
        await websocket.send(response.model_dump_json())
    except Exception as e:
        print(f"Error sending to websocket: {e}")