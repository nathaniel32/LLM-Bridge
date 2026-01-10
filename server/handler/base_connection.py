from typing import TYPE_CHECKING
from fastapi import WebSocket, WebSocketDisconnect
from server.utils import ws_response
import logging
from abc import ABC, abstractmethod
from common.models import MessageModel, StatusType, ResponseModel
from server.models import RequestError
import json

if TYPE_CHECKING:
    from server.handler.connection_manager import ConnectionManager

class BaseConnection(ABC):
    def __init__(self, connection_manager:"ConnectionManager", connection: WebSocket):
        self.connection_manager = connection_manager
        self.connection = connection

    async def send(self, message=None, content=None, action=None):
        await ws_response(websockets=[self.connection], action=action, message=message, content=content)

    @abstractmethod
    async def event_handler(self, response_model:ResponseModel):
        pass

    @abstractmethod
    async def cleanup_connection(self):
        pass

    async def _event_listener(self):
        try:
            while True:
                event_data = await self.connection.receive()

                if event_data.get("text"):
                    try:
                        response_model = ResponseModel(**json.loads(event_data["text"]))
                        await self.event_handler(response_model)
                    except RequestError as e:
                        await self.send(message=MessageModel(text=str(e), status=StatusType.WARNING))
                    except Exception as e:
                        logging.exception(f"Error: {e}")
                        await self.send(message=MessageModel(text="Listener Error", status=StatusType.ERROR))

        except WebSocketDisconnect:
            logging.info("WebSocket disconnected")
        except Exception as e:
            logging.error("Unexpected error in websocket listener")
        finally:
            await self.cleanup_connection()
    
    async def bind(self):
        await self._event_listener()