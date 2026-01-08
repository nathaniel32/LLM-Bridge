from server.handler.group_connection import GroupConnection
from server.handler.worker_connection import WorkerConnection
from typing import List
import asyncio

class ConnectionManager:
    def __init__(self):
        self.group_connections: List[GroupConnection] = []
        self.worker_connections: List[WorkerConnection] = []
        self.waiting_groups: List[GroupConnection] = []
        self._group_lock = asyncio.Lock()
        self._worker_lock = asyncio.Lock()
        self._dispatch_lock = asyncio.Lock()

    # send to all groups
    async def _broadcast(self):
        async with self._group_lock:
            groups = self.group_connections.copy()
        
        # Lockless broadcast (avoids deadlock)
        for group_connection in groups:
            print(group_connection)

    # add group connection
    async def add_group_connection(self) -> GroupConnection:
        async with self._group_lock:
            connection = GroupConnection(self)
            self.group_connections.append(connection)
            print("Active Group connection: ", len(self.group_connections))
        
        return connection
    
    # remove group connection
    async def remove_group_connection(self, connection: GroupConnection):
        async with self._group_lock:
            if connection in self.group_connections:
                self.group_connections.remove(connection)
                print("Group connection removed: ", len(self.group_connections))
        
        await self._broadcast()

    async def add_worker_connection(self) -> WorkerConnection:
        async with self._worker_lock:
            connection = WorkerConnection(self)
            self.worker_connections.append(connection)
            print("Active worker connection: ", len(self.worker_connections))
        
        await self._broadcast()
        return connection

    async def remove_worker_connection(self, connection: WorkerConnection):
        async with self._worker_lock:
            if connection in self.worker_connections:
                self.worker_connections.remove(connection)
                print("Worker connection removed: ", len(self.worker_connections))
        
        await self._broadcast()