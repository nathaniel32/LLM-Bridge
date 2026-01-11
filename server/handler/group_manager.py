from typing import TYPE_CHECKING, List, Optional
from common.models import StatusType, ClientContent, MessageModel, AbortException, GroupInfos, InteractionStatus, GroupCredential, GroupStatus
from server.models import ChatContext
from uuid import uuid4

if TYPE_CHECKING:
    from server.handler.connection_manager import ConnectionManager
    from server.handler.worker_connection import WorkerConnection
    from server.handler.client_connection import ClientConnection

class GroupManager:
    def __init__(self, connection_manager:"ConnectionManager"):
        self.group_infos = GroupInfos(credential=GroupCredential(id=uuid4().hex, title="unnamed"))
        self.connection_manager = connection_manager
        self.client_connections: List[ClientConnection] = []
        self.worker_connection: Optional["WorkerConnection"] = None
        self.chat_context = ChatContext()

    async def reset_state(self):
        await self.update_group_infos(status=GroupStatus.IDLE)
        self.chat_context.close_active_interaction()
        self.worker_connection = None

    async def add_client(self, client_connection:"ClientConnection"):
        if client_connection.group_manager is not None: await client_connection.group_manager.remove_client(client_connection) # leave prev group

        self.client_connections.append(client_connection)
        client_connection.group_manager = self
        await client_connection.send(message=MessageModel(text=f"Joined to {self.group_infos.credential.id}"), content=ClientContent(joined_group_infos=self.group_infos))
        for interaction in self.chat_context.interaction_history:
            await self.update_interaction(interaction=interaction, client_connections=[client_connection])
    
    async def remove_client(self, client_connection:"ClientConnection"):
        self.client_connections.remove(client_connection)
        client_connection.group_manager = None
        empty_group_infos = GroupInfos(credential=GroupCredential(id="", title=""))
        await client_connection.send(message=MessageModel(text=f"Leave from {self.group_infos.credential.id}", status=StatusType.WARNING), content=ClientContent(joined_group_infos=empty_group_infos)) # reset joined_group_infos

    async def delete_group(self):
        await self.connection_manager.remove_group_manager(self)
        await self.abort_interaction()
        for client in self.client_connections[:]: # copy
            await self.remove_client(client)

    async def send(self, message=None, content=None, action=None, client_connections=None):
        if client_connections is None:
            client_connections = self.client_connections

        for client_connection in client_connections:
            await client_connection.send(action=action, message=message, content=content)

    async def update_interaction(self, interaction=None, status:Optional[InteractionStatus]=None, client_connections=None):
        if interaction is None:
            interaction = self.chat_context.active_interaction
        
        if interaction is not None:
            if status:
                interaction.status = status
            
            await self.send(content=ClientContent(interaction=interaction), client_connections=client_connections)

    async def update_group_infos(self, status:Optional[GroupStatus]=None, client_connections=None, update_credential=False):
        if status is not None:
            self.group_infos.status = status

        if update_credential:
            self.group_infos.credential.title = self.chat_context.title_interaction.response
            await self.connection_manager.broadcast(content=ClientContent(groups_credential=self.connection_manager._get_groups_credential()))
        await self.send(content=ClientContent(joined_group_infos=self.group_infos), client_connections=client_connections)

    async def register_job(self):
        await self.update_group_infos(status=GroupStatus.PROCESSING)
        await self.update_interaction(status=InteractionStatus.QUEUED)
        await self.connection_manager.enqueue_job(group_manager=self)
        await self.send(message=MessageModel(text="register job"))

    async def create_interaction(self, prompt):
        self.chat_context.create_interaction(prompt)
        await self.register_job()

    async def edit_interaction(self, prompt, interaction_id):
        self.chat_context.edit_interaction(interaction_id, prompt)
        await self.register_job()
        
    async def start_job(self):
        try:
            await self.update_interaction(status=InteractionStatus.PROCESSING)

            await self.send(message=MessageModel(text="Starting process..."))
            await self.worker_connection.send_job(self)
            
            await self.send(message=MessageModel(text="Process completed!"))
            await self.update_interaction(status=InteractionStatus.COMPLETED)
        except AbortException as e:
            await self.update_interaction(status=InteractionStatus.ABORTED)
            await self.send(message=MessageModel(text=str(e), status=StatusType.WARNING))
        except Exception as e:
            await self.update_interaction(status=InteractionStatus.FAILED)
            await self.send(message=MessageModel(text=str(e), status=StatusType.ERROR))
        finally:
            await self.reset_state()

    async def abort_interaction(self):
        await self.send(message=MessageModel(text="trying to abort request...", status=StatusType.WARNING))
        await self.connection_manager.remove_from_queue(self)
        
        if self.worker_connection:
            await self.worker_connection.abort_interaction()
        else:
            await self.update_interaction(status=InteractionStatus.ABORTED)
            await self.send(message=MessageModel(text="Aborted!!", status=StatusType.WARNING))
            await self.reset_state()

    async def delete_interaction(self, interaction_id):
        interaction = self.chat_context.delete_interaction(interaction_id=interaction_id)
        await self.update_interaction(interaction=interaction, status=InteractionStatus.DELETED)