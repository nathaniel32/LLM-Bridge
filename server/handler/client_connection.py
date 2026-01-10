from typing import TYPE_CHECKING
from fastapi import WebSocket, WebSocketDisconnect
import logging
from server.utils import ws_response
from server.handler.group_manager import GroupManager
if TYPE_CHECKING:
    from server.handler.connection_manager import ConnectionManager

class ClientConnection:
    def __init__(self, connection_manager:"ConnectionManager", connection: WebSocket):
        self.connection_manager = connection_manager
        self.connection = connection

    async def send(self, message=None, content=None, action=None):
        await ws_response(websockets=[self.connection], action=action, message=message, content=content)

    async def _event_listener(self):
        group_manager = await self.connection_manager.add_group_manager()
        await group_manager.add_client(self)

        try:
            while True:
                event_data = await self.connection.receive()

                if event_data.get("text"):
                    await group_manager.event_handler(event_data)

        except WebSocketDisconnect:
            logging.info("WebSocket disconnected")
        except Exception as e:
            logging.exception("Unexpected error in websocket listener")
        finally:
            logging.info("END!")
    
    async def bind(self):
        await self._event_listener()