from handler.client_connection import ClientConnection
from handler.worker_connection import WorkerConnection
from typing import List
import asyncio

class ConnectionManager:
    def __init__(self):
        self.client_sessions: List[ClientConnection] = []
        self.worker_sessions: List[WorkerConnection] = []
        self.waiting_clients: List[ClientConnection] = []
        self._client_lock = asyncio.Lock()  # Lock for client operations
        self._worker_lock = asyncio.Lock()    # Lock for worker operations
        self._dispatch_lock = asyncio.Lock()