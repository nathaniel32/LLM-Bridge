import json
from fastapi import WebSocket, WebSocketDisconnect
from typing import TYPE_CHECKING, List, Optional
from common.models import ClientServerActionType, ServerClientActionType, StatusType, JobStatus, ClientContent, MessageModel, ResponseModel, StreamResponseContent
from server.utils import ws_response
import logging
from pydantic import BaseModel
if TYPE_CHECKING:
    from server.handler.connection_manager import ConnectionManager
    from server.handler.worker_connection import WorkerConnection

class Interaction(BaseModel):
    prompt: str
    response: str

class LiveInteraction(BaseModel):
    prompt: Optional[str] = None
    response_stream_history: List[StreamResponseContent] = []

    def get_full_interaction(self) -> Interaction:
        combined_response = "".join([item.response for item in self.response_stream_history])
        return Interaction(prompt=self.prompt, response=combined_response)
    
    def clear(self):
        self.prompt = None
        self.response_stream_history.clear()

class GroupManager:
    def __init__(self, connection_manager:"ConnectionManager"):
        self.connection_manager = connection_manager
        self.client_connections: List[WebSocket] = []
        self.worker_connection: Optional["WorkerConnection"] = None
        self.interaction_history: List[Interaction] = []
        self.live_interaction = LiveInteraction()

    async def send(self, message=None, content=None, action=None, connections=None):
        if connections is None:
            connections = self.client_connections

        await ws_response(websockets=connections, action=action, message=message, content=content)

    async def prompt_handler(self, prompt):
        self.live_interaction.prompt = prompt
        await self.connection_manager.enqueue_job(group_manager=self)
        self.status = JobStatus.QUEUED
        await self.send(content=ClientContent(job_status=self.status))

    async def start_process(self):
        self.status = JobStatus.IN_PROGRESS
        await self.send(message=MessageModel(text="Starting process..."), content=ClientContent(job_status=self.status))
        await self.worker_connection.prompt(self)
        self.interaction_history.append(self.live_interaction.get_full_interaction())
        self.live_interaction.clear()

    async def _event_listener(self, websocket:WebSocket):
        try:
            while True:
                event_data = await websocket.receive()

                if event_data.get("text"):
                    try:
                        response_model = ResponseModel(**json.loads(event_data["text"]))
                        
                        match response_model.action:
                            case ClientServerActionType.PROMPT:
                                await self.prompt_handler(prompt=response_model.content.prompt)
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