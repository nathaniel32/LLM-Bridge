from fastapi import WebSocket
from typing import TYPE_CHECKING, List
if TYPE_CHECKING:
    from server.handler.connection_manager import ConnectionManager

class GroupManager:
    def __init__(self, connection_manager:"ConnectionManager"):
        self.connection_manager = connection_manager
        self.client_connections: List[WebSocket] = []

    async def bind(self, websocket:WebSocket):
        self.client_connections.append(websocket)
        print("client online: ", len(self.client_connections))