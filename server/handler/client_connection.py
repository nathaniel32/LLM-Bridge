from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from server.handler.connection_manager import ConnectionManager

class ClientConnection:
    def __init__(self, connection_manager:"ConnectionManager"):
        self.connection_manager = connection_manager

    async def bind(self):
        pass