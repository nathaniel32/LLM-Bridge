from typing import TYPE_CHECKING
from fastapi import WebSocket, WebSocketDisconnect
from common.models import WorkerServerActionType, StatusType
import logging
import json
from server.utils import ws_response
if TYPE_CHECKING:
    from server.handler.connection_manager import ConnectionManager

class WorkerConnection:
    def __init__(self, connection_manager:"ConnectionManager", connection: WebSocket):
        self.connection_manager = connection_manager
        self.connection = connection

    async def send(self, action, content=None):
        await ws_response(websockets=[self.connection], action=action, content=content)

    async def _message_listener(self):
        try:
            while True:
                message = await self.connection.receive()

                if message.get("text"):
                    try:
                        data = json.loads(message["text"])
                        action = data.get("action")

                        match action:
                            case WorkerServerActionType.LOG:
                                pass
                            case _:
                                await self.send(message="Unknown action", message_status=StatusType.ERROR)
                    except Exception:
                        await self.send(message=message.get("text"))

        except WebSocketDisconnect:
            logging.info("WebSocket disconnected")
        except Exception as e:
            logging.exception("Unexpected error in websocket listener")
        finally:
            logging.info("END!")

    async def bind(self):
        await self._message_listener()