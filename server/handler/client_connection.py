from typing import TYPE_CHECKING, Optional
from fastapi import WebSocket
from server.handler.group_manager import GroupManager
from server.handler.base_connection import BaseConnection
from server.models import RequestError
from common.models import ResponseModel, ClientServerActionType, ClientContent, ServerClientActionType, MessageModel, StatusType
import asyncio

if TYPE_CHECKING:
    from server.handler.connection_manager import ConnectionManager

class ClientConnection(BaseConnection):
    def __init__(self, connection_manager:"ConnectionManager", connection: WebSocket):
        super().__init__(connection_manager, connection)
        self.group_manager: Optional[GroupManager] = None
        self.heartbeat: Optional[asyncio.Task[None]] = None

    async def heartbeat_task(self):
        try:
            while True:
                await asyncio.sleep(2)
                await self.send(action=ServerClientActionType.HEARTBEAT)
        except asyncio.CancelledError:
            print("CancelledError")
        except Exception as e:
            await self.send(message=MessageModel(text=f"Heartbeat error: {e}", status=StatusType.ERROR))

    async def setup_connection(self):
        self.heartbeat = asyncio.create_task(self.heartbeat_task())
        client_content = ClientContent(
            joined_group_infos = "",
            client_num = len(self.connection_manager.client_connections),
            worker_num = len(self.connection_manager.worker_connections),
            group_num = len(self.connection_manager.group_managers),
            groups_infos = self.connection_manager._get_groups_infos(),
            queue_length = len(self.connection_manager.waiting_groups)
        )
        await self.send(content=client_content)

    async def cleanup_connection(self):
        if self.heartbeat is not None:
            self.heartbeat.cancel()
            await self.heartbeat
        if self.group_manager is not None: await self.group_manager.remove_client(self)
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
            case ClientServerActionType.CREATE_INTERACTION:
                if self.group_manager is None:
                    group = await self.connection_manager.add_group_manager()
                    await group.add_client(self)
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
                raise RequestError("Unknown action")