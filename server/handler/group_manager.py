import json
from fastapi import WebSocket, WebSocketDisconnect
from typing import TYPE_CHECKING, List, Optional
from common.models import ClientServerActionType, StatusType, JobStatus, ClientContent, MessageModel, ResponseModel, Interaction
from server.utils import ws_response
import logging
from pydantic import BaseModel

if TYPE_CHECKING:
    from server.handler.connection_manager import ConnectionManager
    from server.handler.worker_connection import WorkerConnection

class ChatContext(BaseModel):
    system: Optional[str] = "You are a helpful assistant."
    interaction_history: List[Interaction] = []
    active_interaction: Optional[Interaction] = None

    def create_interaction(self, prompt):
        self.active_interaction = Interaction(prompt=prompt)
        self.interaction_history.append(self.active_interaction)

    def finish_interaction(self):
        self.active_interaction = None

    def edit_interaction(self, interaction_id, prompt):
        self.active_interaction = next((i for i in self.interaction_history if i.id == interaction_id), None)
        self.active_interaction.prompt = prompt
        self.active_interaction.response = ""
    
    def get_chat_message(self):
        messages = []
        if self.system:
            messages.append({"role": "system", "content": self.system})
        for interaction in self.interaction_history:
            messages.append({"role": "user", "content": interaction.prompt})
            if interaction is not self.active_interaction:
                messages.append({"role": "assistant", "content": interaction.response})
            else:
                break
        return json.dumps(messages)

class GroupManager:
    def __init__(self, connection_manager:"ConnectionManager"):
        self.connection_manager = connection_manager
        self.client_connections: List[WebSocket] = []
        self.worker_connection: Optional["WorkerConnection"] = None
        self.chat_context = ChatContext()
        self.abort = False

    async def send(self, message=None, content=None, action=None, connections=None):
        if connections is None:
            connections = self.client_connections

        await ws_response(websockets=connections, action=action, message=message, content=content)

    async def register_job(self):
        await self.connection_manager.enqueue_job(group_manager=self)
        self.status = JobStatus.QUEUED
        await self.send(content=ClientContent(job_status=self.status))

    async def create_job(self, prompt):
        self.chat_context.create_interaction(prompt)
        await self.register_job()
    
    async def edit_job(self, prompt, id):
        self.chat_context.edit_interaction(id, prompt)
        await self.register_job()

    async def start_process(self):
        self.status = JobStatus.IN_PROGRESS
        await self.send(message=MessageModel(text="Starting process..."), content=ClientContent(job_status=self.status))
        await self.worker_connection.send_job(self)
        self.chat_context.finish_interaction()

    async def abort_process(self):
        self.abort = True
        await self.send(message=MessageModel(text="trying to abort request...", status=StatusType.WARNING))
        if self.worker_connection:
            await self.worker_connection.abort_job()
    
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
                            case ClientServerActionType.EDIT_JOB:
                                await self.edit_job(prompt=response_model.content.input_text, id=response_model.content.input_id)
                            case _:
                                await self.send(message=MessageModel(text="Unknown action", status=StatusType.ERROR))
                    except Exception as e:
                        logging.exception(f"Error: {e}")
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