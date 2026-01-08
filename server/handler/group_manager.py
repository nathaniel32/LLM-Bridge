import json
from fastapi import WebSocket, WebSocketDisconnect
from typing import TYPE_CHECKING, List, Optional
from common.models import ClientServerActionType, ServerClientActionType, StatusType, JobStatus, ClientContent
from server.utils import ws_response
import logging
if TYPE_CHECKING:
    from server.handler.connection_manager import ConnectionManager
    from server.handler.worker_connection import WorkerConnection

class GroupManager:
    def __init__(self, connection_manager:"ConnectionManager"):
        self.connection_manager = connection_manager
        self.client_connections: List[WebSocket] = []
        self.worker_connection: Optional["WorkerConnection"] = None

    async def send(self, message=None, message_status=StatusType.INFO, content=None, action=ServerClientActionType.LOG, connections=None):
        print(message)
        if connections is None:
            connections = self.client_connections

        await ws_response(websockets=connections, action=action, message=message, content=content, message_status=message_status)

    async def _message_listener(self, websocket:WebSocket):
        try:
            while True:
                message = await websocket.receive()

                if message.get("text"):
                    try:
                        data = json.loads(message["text"])
                        action = data.get("action")

                        match action:
                            case ClientServerActionType.PROMPT:
                                await self.connection_manager.enqueue_job(group_manager=self)
                                self.status = JobStatus.QUEUED
                                await self.send(content=ClientContent(job_status=self.status))
                            case _:
                                await self.send(message="Unknown action", message_status=StatusType.ERROR)
                    except Exception:
                        await self.send(message=message.get("text"))

        except WebSocketDisconnect:
            logging.info("WebSocket disconnected")
        except Exception as e:
            logging.exception("Unexpected error in websocket listener")
        finally:
            logging.info("END!")

    async def start_process():
        print("START")

    async def bind(self, websocket:WebSocket):
        self.client_connections.append(websocket)
        print("client online: ", len(self.client_connections))
        await self._message_listener(websocket)