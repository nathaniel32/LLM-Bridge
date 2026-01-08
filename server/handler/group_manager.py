import json
from fastapi import WebSocket, WebSocketDisconnect
from typing import TYPE_CHECKING, List
from common.models import ClientServerActionType, ServerClientActionType, StatusType
from server.utils import ws_response
if TYPE_CHECKING:
    from server.handler.connection_manager import ConnectionManager

class GroupManager:
    def __init__(self, connection_manager:"ConnectionManager"):
        self.connection_manager = connection_manager
        self.client_connections: List[WebSocket] = []

    async def send(self, message=None, status_type=StatusType.INFO, content=None, action=ServerClientActionType.LOG, connections=None):
        print(message)
        if connections is None:
            connections = self.client_connections

        await ws_response(websockets=connections, action=action, message=message, content=content, status_type=status_type)

    async def _message_listener(self, websocket:WebSocket):
        try:
            while True:
                try:
                    message = await websocket.receive()
                except WebSocketDisconnect as e:
                    raise Exception(f"- WebSocketDisconnect: {e}") from e
                except RuntimeError as e:
                    raise Exception(f"- RuntimeError: {e}") from e

                print(message)
                if message.get("text"):
                    data = json.loads(message["text"])
                    action = data.get("action")

                    match action:
                        case ClientServerActionType.ABORT_REQUEST:
                            pass
                        case _:
                            await self.send(message="Unknown action", status_type=StatusType.ERROR)

        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            print("stop")

    async def bind(self, websocket:WebSocket):
        self.client_connections.append(websocket)
        print("client online: ", len(self.client_connections))
        await self._message_listener(websocket)