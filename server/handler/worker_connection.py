from typing import TYPE_CHECKING, Optional, Protocol, Any
from fastapi import WebSocket
from common.models import WorkerServerActionType, ServerWorkerActionType, InputContent, ResponseModel, MessageModel, ResponseStreamContent, AbortException, StatusType
from server.handler.group_manager import GroupManager
import asyncio
import logging
from server.models import InteractionType
from server.handler.base_connection import BaseConnection
if TYPE_CHECKING:
    from server.handler.connection_manager import ConnectionManager

class SendCallback(Protocol):
    async def __call__(
        self, 
        message: Optional[Any] = None, 
        content: Optional[Any] = None, 
        action: Optional[Any] = None
    ) -> None:
        ...

class WorkerTaskManager:
    def __init__(self, group_manager, send_callback: SendCallback):
        self.job_event = asyncio.Event()
        self.unsuccess_action: Optional[WorkerServerActionType] = None
        self.group_manager: GroupManager = group_manager
        self.send_back = send_callback

    async def event_handler(self, response_model:ResponseModel):
        await self.send_back(message=response_model.message)

        match response_model.action:
            case WorkerServerActionType.STREAM_RESPONSE:
                assert isinstance(response_model.content, ResponseStreamContent)
                if self.group_manager.chat_context.interaction_type == InteractionType.CHAT:
                    self.group_manager.chat_context.active_interaction.add_response_chunk(response_model.content.response)
                    await self.group_manager.update_interaction() # stream
                elif self.group_manager.chat_context.interaction_type == InteractionType.TITLE:
                    self.group_manager.chat_context.title_interaction.add_response_chunk(response_model.content.response)
                    await self.group_manager.update_group_infos(update_credential=True)
            case WorkerServerActionType.ABORTED:
                self.worker_unsuccess_action = response_model.action
            case WorkerServerActionType.ERROR:
                self.worker_unsuccess_action = response_model.action
            case WorkerServerActionType.END:
                self.job_event.set()

class WorkerConnection(BaseConnection):
    def __init__(self, connection_manager:"ConnectionManager", connection: WebSocket):
        super().__init__(connection_manager, connection)
        self.active_task: Optional[WorkerTaskManager] = None

    async def reset_state(self):
        self.active_task = None # open worker
        await self.connection_manager.dequeue_job()

    async def send_abort_request(self):
        if self.active_task:
            await self.send(action=ServerWorkerActionType.ABORT_INTERACTION)
            await self.active_task.send_back(message=MessageModel(text="Job abort request sended to Worker"))

    async def send_job(self, group_manager:GroupManager, input_text):
        self.active_task = WorkerTaskManager(group_manager=group_manager, send_callback=group_manager.send)
        try:
            await self.active_task.send_back(message=MessageModel(text="Sending Job to Worker..."))
            await self.send(action=ServerWorkerActionType.CREATE_INTERACTION, content=InputContent(input_text=input_text))
            await self.active_task.job_event.wait()

            if self.active_task.unsuccess_action == WorkerServerActionType.ERROR:
                raise Exception(self.active_task.unsuccess_action)
            if self.active_task.unsuccess_action == WorkerServerActionType.ABORTED:
                raise AbortException(self.active_task.unsuccess_action)
        except AbortException as e:
            raise AbortException(f"Abort in Worker: {e}") from e
        except Exception as e:
            raise Exception(f"Error in Worker: {e}") from e
        
    async def setup_connection(self):
        await self.reset_state()
    
    async def cleanup_connection(self):
        logging.info("Worker disconnected!")
        await self.connection_manager.remove_worker_connection(connection=self)
        if self.active_task:
            await self.active_task.send_back(message=MessageModel(text="Worker disconnected!", status=StatusType.ERROR))
            self.worker_unsuccess_action = WorkerServerActionType.ERROR
            self.active_task.job_event.set()

    async def event_handler(self, response_model:ResponseModel):
        await self.active_task.event_handler(response_model=response_model)