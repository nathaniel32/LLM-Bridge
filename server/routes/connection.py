from fastapi import APIRouter, WebSocket, status
from common.models import StatusType, ServerWorkerActionType
from common.utils import config
from server.utils import ws_response
from server.handler.connection_manager import ConnectionManager

class Connection:
    def __init__(self):
        self.router = APIRouter(prefix="/connection", tags=["Connection"])
        self.connection_manager = ConnectionManager()

    async def client_ws_endpoint(self, websocket: WebSocket):
        await websocket.accept()
        session = await self.connection_manager.add_client_session()
        await session.bind(websocket)

    async def worker_ws_endpoint(self, websocket: WebSocket):
        await websocket.accept()
        key = websocket.cookies.get("access_key")

        if key != config.WORKER_ACCESS_KEY:
            await ws_response(websockets=[websocket], message="Unauthorized: Invalid key", status_type=StatusType.ERROR, action=ServerWorkerActionType.LOG)
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return
        
        session = await self.connection_manager.add_worker_session(websocket)
        await session.bind()