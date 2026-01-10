import json
from fastapi import WebSocket
from typing import TYPE_CHECKING, List, Optional
from common.models import ClientServerActionType, StatusType, JobStatus, ClientContent, MessageModel, ResponseModel, AbortException, GroupInfos
from server.utils import ws_response
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
        self.job_status = JobStatus.IDLE

    def reset_state(self):
        self.chat_context.finish_interaction()
        self.worker_connection = None
        self.job_status = JobStatus.IDLE

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
        self.job_status = JobStatus.QUEUED
        await self.send(content=ClientContent(job_status=self.job_status))

    async def create_interaction(self, prompt):
        self.chat_context.create_interaction(prompt)
        await self.register_job()
    
    async def edit_interaction(self, prompt, interaction_id):
        self.chat_context.edit_interaction(interaction_id, prompt)
        await self.register_job()

    async def start_job(self):
        try:
            self.job_status = JobStatus.IN_PROGRESS
            await self.send(message=MessageModel(text="Starting process..."), content=ClientContent(job_status=self.job_status))
            await self.worker_connection.send_job(self)
            
            self.job_status = JobStatus.IDLE
            await self.send(message=MessageModel(text="Process completed!"), content=ClientContent(job_status=self.job_status))
        except AbortException as e:
            self.job_status = JobStatus.ABORTED
            await self.send(message=MessageModel(text=str(e), status=StatusType.WARNING), content=ClientContent(job_status=self.job_status))
        except Exception as e:
            self.job_status = JobStatus.FAILED
            await self.send(message=MessageModel(text=str(e), status=StatusType.ERROR), content=ClientContent(job_status=self.job_status))
        finally:
            self.reset_state()

    async def abort_interaction(self):
        if self.job_status in [JobStatus.IDLE, JobStatus.ABORTED, JobStatus.FAILED]:
            await self.send(message=MessageModel(text="No job is currently running", status=StatusType.WARNING))
            return
        
        await self.send(message=MessageModel(text="trying to abort request...", status=StatusType.WARNING))
        await self.connection_manager.remove_from_queue(self)
        if self.job_status == JobStatus.IN_PROGRESS:
            await self.worker_connection.abort_interaction()
        else:
            self.reset_state()

    async def delete_interaction(self, interaction_id):
        interaction = self.chat_context.delete_interaction(interaction_id=interaction_id)
        await self.update_active_interaction(interaction=interaction)

    async def event_handler(self, event_data):
        try:
            response_model = ResponseModel(**json.loads(event_data["text"]))
            
            match response_model.action:
                case ClientServerActionType.CREATE_INTERACTION:
                    await self.create_interaction(prompt=response_model.content.input_text)
                case ClientServerActionType.ABORT_INTERACTION:
                    await self.abort_interaction()
                case ClientServerActionType.DELETE_INTERACTION:
                    await self.delete_interaction(interaction_id=response_model.content.input_id)
                case ClientServerActionType.EDIT_INTERACTION:
                    await self.edit_interaction(prompt=response_model.content.input_text, interaction_id=response_model.content.input_id)
                case _:
                    await self.send(message=MessageModel(text="Unknown action", status=StatusType.ERROR))

        except JobRequestError as e:
            await self.send(message=MessageModel(text=str(e), status=StatusType.WARNING))
        except Exception as e:
            await self.send(message=MessageModel(text=str(e), status=StatusType.ERROR))