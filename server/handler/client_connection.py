from typing import TYPE_CHECKING, Optional
from fastapi import WebSocket
from server.handler.group_manager import GroupManager
from server.handler.base_connection import BaseConnection
from server.models import RequestError
from common.models import ResponseModel, ClientServerActionType, MessageModel, StatusType, ClientContent

if TYPE_CHECKING:
    from server.handler.connection_manager import ConnectionManager

class ClientConnection(BaseConnection):
    def __init__(self, connection_manager:"ConnectionManager", connection: WebSocket):
        super().__init__(connection_manager, connection)
        self.group_manager: Optional[GroupManager] = None

    async def setup_connection(self):
        client_content = ClientContent(
            joined_group_id = "",
            client_num = len(self.connection_manager.client_connections),
            worker_num = len(self.connection_manager.worker_connections),
            group_num = len(self.connection_manager.group_managers),
            groups_infos = self.connection_manager._get_groups_infos(),
            queue_length = len(self.connection_manager.waiting_groups)
        )
        await self.send(content=client_content)

    async def cleanup_connection(self):
        await self.connection_manager.remove_client_connection(self)

    async def event_handler(self, response_model:ResponseModel):
        match response_model.action:
            case ClientServerActionType.CREATE_GROUP:
                group = await self.connection_manager.add_group_manager()
                await group.add_client(self)
            case ClientServerActionType.DELETE_GROUP:
                group = self.connection_manager.get_group_by_id(group_id=response_model.content.input_id)
                await group.delete_group()
            case ClientServerActionType.JOIN_GROUP:
                group = self.connection_manager.get_group_by_id(group_id=response_model.content.input_id)
                await group.add_client(self)
            case ClientServerActionType.LEAVE_GROUP:
                if self.group_manager is None:
                    raise RequestError("Group not found!")
                await self.group_manager.remove_client(self)
                self.group_manager = None
            case ClientServerActionType.CREATE_INTERACTION:
                if self.group_manager is None:
                    raise RequestError("Group not found!")
                await self.group_manager.create_interaction(prompt=response_model.content.input_text)
            case ClientServerActionType.ABORT_INTERACTION:
                if self.group_manager is None:
                    raise RequestError("Group not found!")
                await self.group_manager.abort_interaction()
            case ClientServerActionType.DELETE_INTERACTION:
                if self.group_manager is None:
                    raise RequestError("Group not found!")
                await self.group_manager.delete_interaction(interaction_id=response_model.content.input_id)
            case ClientServerActionType.EDIT_INTERACTION:
                if self.group_manager is None:
                    raise RequestError("Group not found!")
                await self.group_manager.edit_interaction(prompt=response_model.content.input_text, interaction_id=response_model.content.input_id)
            case _:
                await self.send(message=MessageModel(text="Unknown action", status=StatusType.ERROR))