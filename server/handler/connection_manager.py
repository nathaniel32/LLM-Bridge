from server.handler.client_connection import ClientConnection
from server.handler.worker_connection import WorkerConnection
from typing import List
import asyncio

class ConnectionManager:
    def __init__(self):
        self.client_sessions: List[ClientConnection] = []
        self.worker_sessions: List[WorkerConnection] = []
        self.waiting_clients: List[ClientConnection] = []
        self._client_lock = asyncio.Lock()
        self._worker_lock = asyncio.Lock()
        self._dispatch_lock = asyncio.Lock()

    # send to all clients
    async def _broadcast(self):
        async with self._client_lock:
            clients = self.client_sessions.copy()
        
        # Lockless broadcast (avoids deadlock)
        for client_session in clients:
            print(client_session)

    # save uniq session per client
    async def add_client_session(self) -> ClientConnection:
        async with self._client_lock:
            session = ClientConnection(self)
            self.client_sessions.append(session)
            print("Active Client session: ", len(self.client_sessions))
        
        return session
    
    # remove client session
    async def remove_client_session(self, session: ClientConnection):
        async with self._client_lock:
            if session in self.client_sessions:
                self.client_sessions.remove(session)
                print("Client session removed: ", len(self.client_sessions))
        
        await self._broadcast()

    async def add_worker_session(self) -> WorkerConnection:
        async with self._worker_lock:
            session = WorkerConnection(self)
            self.worker_sessions.append(session)
            print("Active worker session: ", len(self.worker_sessions))
        
        await self._broadcast()
        return session

    async def remove_worker_session(self, session: WorkerConnection):
        async with self._worker_lock:
            if session in self.worker_sessions:
                self.worker_sessions.remove(session)
                print("Worker session removed: ", len(self.worker_sessions))
        
        await self._broadcast()