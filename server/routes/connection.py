from fastapi import APIRouter, WebSocket, status
from common.models import StatusType, ServerWorkerActionType
from server.setting import config
from server.utils import ws_response
from server.handler.connection_manager import ConnectionManager

class Connection:
    def __init__(self):
        self.router = APIRouter(prefix="/connection", tags=["Connection"])
        self.router.add_api_websocket_route("/client", self.client_endpoint)
        self.router.add_api_websocket_route("/worker", self.worker_endpoint)
        self.connection_manager = ConnectionManager()

    async def client_endpoint(self, websocket: WebSocket):
        await websocket.accept()
        manager = await self.connection_manager.add_group_manager()
        await manager.bind(websocket)

    async def worker_endpoint(self, websocket: WebSocket):
        await websocket.accept()
        key = websocket.cookies.get("access_key")

        if key != config.WORKER_ACCESS_KEY:
            await ws_response(websockets=[websocket], message="Unauthorized: Invalid key", status_type=StatusType.ERROR, action=ServerWorkerActionType.LOG)
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return
        
        connection = await self.connection_manager.add_worker_connection(websocket)
        await connection.bind()