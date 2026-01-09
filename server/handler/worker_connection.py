from typing import TYPE_CHECKING, Optional
from fastapi import WebSocket, WebSocketDisconnect
from common.models import WorkerServerActionType, StatusType, ServerWorkerActionType, CreateJobContent, ResponseModel, MessageModel, ClientContent, ResponseStreamContent
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

    async def send(self, action=None, content=None):
        await ws_response(websockets=[self.connection], action=action, content=content)

    async def send_job(self, group_manager:GroupManager):
        if self.job_event is None:
            try:
                self.job_event = asyncio.Event()
                self.group_manager = group_manager
                await self.group_manager.send(message=MessageModel(text="Sending Job to Worker..."))
                await self.send(action=ServerWorkerActionType.CREATE_JOB, content=CreateJobContent(text_input=group_manager.chat_context.get_chat_message()))
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

                        await self.group_manager.send(message=response_model.message)

                        match response_model.action:    
                            case WorkerServerActionType.STREAM_RESPONSE:
                                assert isinstance(response_model.content, ResponseStreamContent)
                                self.group_manager.chat_context.active_interaction.add_response_chunk(response_model.content.response)
                                await self.group_manager.send(content=ClientContent(interaction=self.group_manager.chat_context.active_interaction)) # stream
                            case WorkerServerActionType.ABORTED:
                                pass
                            case WorkerServerActionType.ERROR:
                                pass
                            case WorkerServerActionType.END:
                                self.job_event.set()
                            case _:
                                pass
                    except Exception as e:
                        logging.exception(f"Exception: {e}")
                        await self.group_manager.send(message=MessageModel(text=str(e), status=StatusType.ERROR))

        except WebSocketDisconnect:
            logging.info("WebSocket disconnected")
        except Exception as e:
            logging.exception("Unexpected error in websocket listener")
        finally:
            logging.info("END!")

    async def bind(self):
        await self.connection_manager.dequeue_job()
        await self._event_listener()