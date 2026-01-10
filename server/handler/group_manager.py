import json
from fastapi import WebSocket, WebSocketDisconnect
from typing import TYPE_CHECKING, List, Optional
from common.models import ClientServerActionType, StatusType, JobStatus, ClientContent, MessageModel, ResponseModel, AbortException, GroupInfos
from server.utils import ws_response
import logging
from server.models import JobRequestError, ChatContext
from uuid import uuid4

if TYPE_CHECKING:
    from server.handler.connection_manager import ConnectionManager
    from server.handler.worker_connection import WorkerConnection

class GroupManager:
    def __init__(self, connection_manager:"ConnectionManager"):
        self.group_infos = GroupInfos(id=uuid4().hex, name="unnamed")
        self.connection_manager = connection_manager
        self.client_connections: List[WebSocket] = []
        self.worker_connection: Optional["WorkerConnection"] = None
        self.chat_context = ChatContext()
        self.job_status = JobStatus.IDLE

    def reset_state(self):
        self.chat_context.finish_interaction()
        self.worker_connection = None
        self.job_status = JobStatus.IDLE

    async def send(self, message=None, content=None, action=None, connections=None):
        if connections is None:
            connections = self.client_connections

        await ws_response(websockets=connections, action=action, message=message, content=content)

    async def update_active_interaction(self, interaction=None):
        if interaction is None:
            interaction = self.chat_context.active_interaction
        await self.send(content=ClientContent(interaction=interaction))

    async def register_job(self):
        await self.update_active_interaction()
        await self.connection_manager.enqueue_job(group_manager=self)
        self.job_status = JobStatus.QUEUED
        await self.send(content=ClientContent(job_status=self.job_status))

    async def create_job(self, prompt):
        self.chat_context.create_interaction(prompt)
        await self.register_job()
    
    async def edit_job(self, prompt, interaction_id):
        self.chat_context.edit_interaction(interaction_id, prompt)
        await self.register_job()

    async def start_process(self):
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

    async def abort_process(self):
        if self.job_status in [JobStatus.IDLE, JobStatus.ABORTED, JobStatus.FAILED]:
            await self.send(message=MessageModel(text="No job is currently running", status=StatusType.WARNING))
            return
        
        await self.send(message=MessageModel(text="trying to abort request...", status=StatusType.WARNING))
        await self.connection_manager.remove_from_queue(self)
        if self.job_status == JobStatus.IN_PROGRESS:
            await self.worker_connection.abort_job()
        else:
            self.reset_state()

    async def delete_job(self, interaction_id):
        interaction = self.chat_context.delete_interaction(interaction_id=interaction_id)
        await self.update_active_interaction(interaction=interaction)
    
    async def _event_listener(self, websocket:WebSocket):
        try:
            while True:
                event_data = await websocket.receive()

                if event_data.get("text"):
                    try:
                        response_model = ResponseModel(**json.loads(event_data["text"]))
                        
                        match response_model.action:
                            case ClientServerActionType.CREATE_JOB:
                                await self.create_job(prompt=response_model.content.input_text)
                            case ClientServerActionType.ABORT_JOB:
                                await self.abort_process()
                            case ClientServerActionType.DELETE_JOB:
                                await self.delete_job(interaction_id=response_model.content.input_id)
                            case ClientServerActionType.EDIT_JOB:
                                await self.edit_job(prompt=response_model.content.input_text, interaction_id=response_model.content.input_id)
                            case _:
                                await self.send(message=MessageModel(text="Unknown action", status=StatusType.ERROR))

                    except JobRequestError as e:
                        await self.send(message=MessageModel(text=str(e), status=StatusType.WARNING))
                    except Exception as e:
                        await self.send(message=MessageModel(text=str(e), status=StatusType.ERROR))

        except WebSocketDisconnect:
            logging.info("WebSocket disconnected")
        except Exception as e:
            logging.error("Unexpected error in websocket listener")
        finally:
            logging.info("END!")

            if websocket in self.client_connections:
                self.client_connections.remove(websocket)
                print("Active Connections: ", len(self.client_connections))

    async def bind(self, websocket:WebSocket):
        self.client_connections.append(websocket)
        print("client online: ", len(self.client_connections))
        await self._event_listener(websocket)