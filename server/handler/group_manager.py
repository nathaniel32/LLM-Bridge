import json
from typing import TYPE_CHECKING, List, Optional
from common.models import ClientServerActionType, StatusType, JobStatus, ClientContent, MessageModel, ResponseModel, AbortException, GroupInfos
from server.models import JobRequestError, ChatContext
from uuid import uuid4

if TYPE_CHECKING:
    from server.handler.connection_manager import ConnectionManager
    from server.handler.worker_connection import WorkerConnection
    from server.handler.client_connection import ClientConnection

class GroupManager:
    def __init__(self, connection_manager:"ConnectionManager"):
        self.group_infos = GroupInfos(id=uuid4().hex, name="unnamed")
        self.connection_manager = connection_manager
        self.client_connections: List[ClientConnection] = []
        self.worker_connection: Optional["WorkerConnection"] = None
        self.chat_context = ChatContext()

    def reset_state(self):
        self.chat_context.finish_interaction()
        self.worker_connection = None

    async def add_client(self, client_connection):
        self.client_connections.append(client_connection)
    
    async def remove_client(self, client_connection):
        self.client_connections.remove(client_connection)

    async def send(self, message=None, content=None, action=None, client_connections=None):
        if client_connections is None:
            client_connections = self.client_connections

        for client_connection in client_connections:
            await client_connection.send(action=action, message=message, content=content)

    async def update_active_interaction(self, interaction=None):
        if interaction is None:
            interaction = self.chat_context.active_interaction
        await self.send(content=ClientContent(interaction=interaction))

    async def register_job(self):
        await self.update_active_interaction()
        await self.connection_manager.enqueue_job(group_manager=self)
        await self.send(message=MessageModel(text="register job"))

    async def create_interaction(self, prompt):
        try:
            self.chat_context.create_interaction(prompt)
            await self.register_job()
        except JobRequestError as e:
            await self.send(message=MessageModel(text=str(e), status=StatusType.WARNING))

    async def edit_interaction(self, prompt, interaction_id):
        try:
            self.chat_context.edit_interaction(interaction_id, prompt)
            await self.register_job()
        except JobRequestError as e:
            await self.send(message=MessageModel(text=str(e), status=StatusType.WARNING))

    async def start_job(self):
        try:
            await self.send(message=MessageModel(text="Starting process..."))
            await self.worker_connection.send_job(self)
            
            await self.send(message=MessageModel(text="Process completed!"))
        except AbortException as e:
            await self.send(message=MessageModel(text=str(e), status=StatusType.WARNING))
        except Exception as e:
            await self.send(message=MessageModel(text=str(e), status=StatusType.ERROR))
        finally:
            self.reset_state()

    async def abort_interaction(self):
        await self.send(message=MessageModel(text="trying to abort request...", status=StatusType.WARNING))
        await self.connection_manager.remove_from_queue(self)
        
        if self.worker_connection:
            await self.worker_connection.abort_interaction()
        else:
            self.reset_state()

    async def delete_interaction(self, interaction_id):
        interaction = self.chat_context.delete_interaction(interaction_id=interaction_id)
        await self.update_active_interaction(interaction=interaction)