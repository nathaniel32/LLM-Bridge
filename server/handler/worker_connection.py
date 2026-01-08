from typing import TYPE_CHECKING
from fastapi import WebSocket, WebSocketDisconnect
from common.models import WorkerServerActionType, StatusType
import logging
import json
if TYPE_CHECKING:
    from server.handler.connection_manager import ConnectionManager

class WorkerConnection:
    def __init__(self, connection_manager:"ConnectionManager"):
        self.connection_manager = connection_manager

    async def _message_listener(self, websocket:WebSocket):
        try:
            while True:
                message = await websocket.receive()

                if message.get("text"):
                    try:
                        data = json.loads(message["text"])
                        action = data.get("action")

                        match action:
                            case WorkerServerActionType.LOG:
                                pass
                            case _:
                                await self.send(message="Unknown action", status_type=StatusType.ERROR)
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