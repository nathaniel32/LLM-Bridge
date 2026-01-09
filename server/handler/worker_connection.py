from typing import TYPE_CHECKING, Optional
from fastapi import WebSocket, WebSocketDisconnect
from common.models import WorkerServerActionType, StatusType, ServerWorkerActionType, PromptContent
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
                await self.group_manager.send("Sending Job to Worker...")
                await self.send(action=ServerWorkerActionType.PROMPT, content=PromptContent(prompt="ok"))
            finally:
                self.job_event = None
                self.group_manager = None
        else:
            raise Exception("Worker busy, please try again later!")

    async def _message_listener(self):
        try:
            while True:
                message = await self.connection.receive()

                if message.get("text"):
                    try:
                        data = json.loads(message["text"])
                        action = data.get("action")

                        match action:
                            case WorkerServerActionType.LOG:
                                pass
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

    async def bind(self):
        await self._message_listener()