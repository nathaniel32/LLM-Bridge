from typing import TYPE_CHECKING, Optional
from fastapi import WebSocket
from server.handler.group_manager import GroupManager
from server.handler.base_connection import BaseConnection
from common.models import ResponseModel, ClientServerActionType, MessageModel, StatusType

if TYPE_CHECKING:
    from server.handler.connection_manager import ConnectionManager

class ClientConnection(BaseConnection):
    def __init__(self, connection_manager:"ConnectionManager", connection: WebSocket):
        super().__init__(connection_manager, connection)
        self.group_manager: Optional[GroupManager] = None

    async def setup_connection(self):
        pass

    async def cleanup_connection(self):
        await self.connection_manager.remove_client_connection(self)

    async def event_handler(self, response_model:ResponseModel):
        match response_model.action:
            case ClientServerActionType.CREATE_GROUP:
                self.group_manager = await self.connection_manager.add_group_manager()
                await self.group_manager.add_client(self)
            case ClientServerActionType.DELETE_GROUP:
                group_id = response_model.content.input_id
                pass
            case ClientServerActionType.JOIN_GROUP:
                self.group_manager = self.connection_manager.get_group_by_id(group_id=response_model.content.input_id)
                await self.group_manager.add_client(self)
            case ClientServerActionType.LEAVE_GROUP:
                await self.group_manager.remove_client(self)
                self.group_manager = None
            case ClientServerActionType.CREATE_INTERACTION:
                await self.group_manager.create_interaction(prompt=response_model.content.input_text)
            case ClientServerActionType.ABORT_INTERACTION:
                await self.group_manager.abort_interaction()
            case ClientServerActionType.DELETE_INTERACTION:
                await self.group_manager.delete_interaction(interaction_id=response_model.content.input_id)
            case ClientServerActionType.EDIT_INTERACTION:
                await self.group_manager.edit_interaction(prompt=response_model.content.input_text, interaction_id=response_model.content.input_id)
            case _:
                await self.send(message=MessageModel(text="Unknown action", status=StatusType.ERROR))