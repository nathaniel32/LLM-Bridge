from typing import TYPE_CHECKING, Optional
from fastapi import WebSocket
from server.handler.group_manager import GroupManager
from server.handler.base_connection import BaseConnection
if TYPE_CHECKING:
    from server.handler.connection_manager import ConnectionManager

class ClientConnection(BaseConnection):
    def __init__(self, connection_manager:"ConnectionManager", connection: WebSocket):
        super().__init__(connection_manager, connection)
        self.group_manager: Optional[GroupManager] = None

    async def event_handler(self, event_data):
        if self.group_manager is None: # dev mode
            self.group_manager = await self.connection_manager.add_group_manager()
            await self.group_manager.add_client(self)

        await self.group_manager.event_handler(event_data)