from typing import TYPE_CHECKING, Optional
from fastapi import WebSocket, WebSocketDisconnect
from common.models import WorkerServerActionType, StatusType, ServerWorkerActionType, PromptContent, ResponseModel, MessageModel, ClientContent
import logging
import json
from server.handler.group_manager import GroupManager
from server.utils import ws_response
import asyncio
if TYPE_CHECKING:
    from server.handler.connection_manager import ConnectionManager

class WorkerConnection:
    def __init__(self, connection_manager:"ConnectionManager", connection: WebSocket):
        self.connection_manager = connection_manager
        self.connection = connection
        self.job_event: Optional[asyncio.Event] = None
        self.group_manager: Optional[GroupManager] = None

    async def send(self, action, content=None):
        await ws_response(websockets=[self.connection], action=action, content=content)

    async def prompt(self, group_manager:GroupManager):
        if self.job_event is None:
            try:
                self.job_event = asyncio.Event()
                self.group_manager = group_manager
                await self.group_manager.send(message=MessageModel(text="Sending Job to Worker..."))
                await self.send(action=ServerWorkerActionType.PROMPT, content=PromptContent(prompt=group_manager.live_interaction.prompt))
                await self.job_event.wait()
            finally:
                self.job_event = None
                self.group_manager = None
                await self.connection_manager.dequeue_job()
        else:
            raise Exception("Worker busy, please try again later!")

    async def _event_listener(self):
        try:
            while True:
                event_data = await self.connection.receive()

                if event_data.get("text"):
                    try:
                        response_model = ResponseModel(**json.loads(event_data["text"]))
                        print(response_model)

                        match response_model.action:
                            case WorkerServerActionType.LOG:
                                await self.group_manager.send(message=response_model.message)
                            case WorkerServerActionType.STREAM_RESPONSE:
                                self.group_manager.live_interaction.response_stream_history.append(response_model.content)
                                await self.group_manager.send(content=ClientContent(response_stream=response_model.content))
                            case WorkerServerActionType.ABORTED:
                                pass
                            case WorkerServerActionType.ERROR:
                                pass
                            case WorkerServerActionType.END:
                                self.job_event.set()
                            case _:
                                await self.group_manager.send(message=MessageModel(text="Worker-Server Unknown action", status=StatusType.ERROR))
                    except Exception:
                        await self.group_manager.send(message=MessageModel(text=event_data.get("text"), status=StatusType.ERROR))

        except WebSocketDisconnect:
            logging.info("WebSocket disconnected")
        except Exception as e:
            logging.exception("Unexpected error in websocket listener")
        finally:
            logging.info("END!")

    async def bind(self):
        await self.connection_manager.dequeue_job()
        await self._event_listener()