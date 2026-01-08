from fastapi import WebSocket
from typing import TYPE_CHECKING, List
if TYPE_CHECKING:
    from server.handler.connection_manager import ConnectionManager

class GroupConnection:
    def __init__(self, connection_manager:"ConnectionManager"):
        self.connection_manager = connection_manager
        self.client_sessions: List[WebSocket] = []

    async def bind(self):
        pass