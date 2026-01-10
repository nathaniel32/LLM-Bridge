from typing import TYPE_CHECKING, Optional
from fastapi import WebSocket
from common.models import WorkerServerActionType, ServerWorkerActionType, InputContent, ResponseModel, MessageModel, ResponseStreamContent, AbortException, StatusType
from server.handler.group_manager import GroupManager
import asyncio
import logging
from server.models import RequestError
from server.handler.base_connection import BaseConnection
if TYPE_CHECKING:
    from server.handler.connection_manager import ConnectionManager

class WorkerConnection(BaseConnection):
    def __init__(self, connection_manager:"ConnectionManager", connection: WebSocket):
        super().__init__(connection_manager, connection)

        self.job_event: Optional[asyncio.Event] = None
        self.group_manager: Optional[GroupManager] = None
        self.worker_unsuccess_action: Optional[WorkerServerActionType] = None

    def reset_state(self):
        self.job_event = None
        self.group_manager = None
        self.worker_unsuccess_action = None

    async def abort_interaction(self):
        if self.job_event:
            await self.send(action=ServerWorkerActionType.ABORT_INTERACTION)
            await self.group_manager.send(message=MessageModel(text="Job abort request sended to Worker"))

    async def send_job(self, group_manager:GroupManager):
        if self.job_event is None:
            try:
                self.job_event = asyncio.Event()
                self.group_manager = group_manager
                await self.group_manager.send(message=MessageModel(text="Sending Job to Worker..."))
                await self.send(action=ServerWorkerActionType.CREATE_INTERACTION, content=InputContent(input_text=group_manager.chat_context.get_chat_message()))
                await self.job_event.wait()
                if self.worker_unsuccess_action == WorkerServerActionType.ERROR:
                    raise Exception(self.worker_unsuccess_action)
                if self.worker_unsuccess_action == WorkerServerActionType.ABORTED:
                    raise AbortException(self.worker_unsuccess_action)
            except AbortException as e:
                raise AbortException(f"Abort in Worker: {e}") from e
            except Exception as e:
                raise Exception(f"Error in Worker: {e}") from e
            finally:
                self.reset_state()
                await self.connection_manager.dequeue_job()
        else:
            raise Exception("Worker busy, please try again later!")
        
    async def setup_connection(self):
        await self.connection_manager.dequeue_job()
        
    async def cleanup_connection(self):
        logging.info("Worker disconnected!")
        await self.connection_manager.remove_worker_connection(connection=self)
        if self.job_event:
            await self.group_manager.send(message=MessageModel(text="Worker disconnected!", status=StatusType.ERROR))
            self.worker_unsuccess_action = WorkerServerActionType.ERROR
            self.job_event.set()

    async def event_handler(self, response_model:ResponseModel):
        await self.group_manager.send(message=response_model.message)

        match response_model.action:    
            case WorkerServerActionType.STREAM_RESPONSE:
                assert isinstance(response_model.content, ResponseStreamContent)
                self.group_manager.chat_context.active_interaction.add_response_chunk(response_model.content.response)
                await self.group_manager.update_interaction() # stream
            case WorkerServerActionType.ABORTED:
                self.worker_unsuccess_action = response_model.action
            case WorkerServerActionType.ERROR:
                self.worker_unsuccess_action = response_model.action
            case WorkerServerActionType.END:
                self.job_event.set()
            case _:
                print(response_model)
                #raise RequestError("Unknown action")