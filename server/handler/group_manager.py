import json
from fastapi import WebSocket, WebSocketDisconnect
from typing import TYPE_CHECKING, List, Optional
from common.models import ClientServerActionType, ServerClientActionType, StatusType, JobStatus, ClientContent, MessageModel, ResponseModel, ResponseStreamContent
from server.utils import ws_response
import logging
from pydantic import BaseModel, Field
if TYPE_CHECKING:
    from server.handler.connection_manager import ConnectionManager
    from server.handler.worker_connection import WorkerConnection

class Interaction(BaseModel):
    prompt: str
    response: str

class ChatContext(BaseModel):
    prompt: Optional[str] = None
    system: Optional[str] = None
    interaction_history: List[Interaction] = []
    response_stream_history: List[ResponseStreamContent] = []

    def clear(self):
        self.prompt = None
        self.response_stream_history.clear()

    def add_interaction(self) -> Interaction:
        combined_response = "".join([item.response for item in self.response_stream_history])
        interaction = Interaction(prompt=self.prompt, response=combined_response)
        self.interaction_history.append(interaction)
        return interaction
    
    def add_response_stream(self, response:ResponseStreamContent):
        self.response_stream_history.append(response)

    def to_json_messages(self):
        messages = []
        if self.system:
            messages.append({"role": "system", "content": self.system})
        for interaction in self.interaction_history:
            messages.append({"role": "user", "content": interaction.prompt})
            messages.append({"role": "assistant", "content": interaction.response})
        return json.dumps(messages, indent=2)

class GroupManager:
    def __init__(self, connection_manager:"ConnectionManager"):
        self.connection_manager = connection_manager
        self.client_connections: List[WebSocket] = []
        self.worker_connection: Optional["WorkerConnection"] = None
        self.chat_context = ChatContext()

    async def send(self, message=None, content=None, action=None, connections=None):
        if connections is None:
            connections = self.client_connections

        await ws_response(websockets=connections, action=action, message=message, content=content)

    async def prompt_handler(self, prompt):
        self.chat_context.prompt = prompt
        await self.connection_manager.enqueue_job(group_manager=self)
        self.status = JobStatus.QUEUED
        await self.send(content=ClientContent(job_status=self.status))

    async def start_process(self):
        self.status = JobStatus.IN_PROGRESS
        await self.send(message=MessageModel(text="Starting process..."), content=ClientContent(job_status=self.status))
        await self.worker_connection.send_job(self)
        self.chat_context.add_interaction()

    async def _event_listener(self, websocket:WebSocket):
        try:
            while True:
                event_data = await websocket.receive()

                if event_data.get("text"):
                    try:
                        response_model = ResponseModel(**json.loads(event_data["text"]))
                        
                        match response_model.action:
                            case ClientServerActionType.CREATE_JOB:
                                await self.prompt_handler(prompt=response_model.content.payload)
                            case _:
                                await self.send(message=MessageModel(text="Unknown action", status=StatusType.ERROR))
                    except Exception as e:
                        await self.send(message=MessageModel(text=str(e), status=StatusType.ERROR))

        except WebSocketDisconnect:
            logging.info("WebSocket disconnected")
        except Exception as e:
            logging.exception("Unexpected error in websocket listener")
        finally:
            logging.info("END!")

    async def bind(self, websocket:WebSocket):
        self.client_connections.append(websocket)
        print("client online: ", len(self.client_connections))
        await self._event_listener(websocket)