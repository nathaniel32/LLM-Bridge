from server.handler.group_manager import GroupManager
from server.handler.worker_connection import WorkerConnection, MessageModel
from typing import List
import asyncio
from server.models import WaitingListError

class ConnectionManager:
    def __init__(self):
        self.group_managers: List[GroupManager] = []
        self.worker_connections: List[WorkerConnection] = []
        self.waiting_groups: List[GroupManager] = []
        self._group_lock = asyncio.Lock()
        self._worker_lock = asyncio.Lock()
        self._dispatch_lock = asyncio.Lock()

    # send to all groups
    async def _broadcast(self):
        async with self._group_lock:
            groups = self.group_managers.copy()
        
        # Lockless broadcast (avoids deadlock)
        for group in groups:
            print(group)

    async def dequeue_job(self):
        async with self._dispatch_lock:
            if self.waiting_groups:
                for worker_connection in self.worker_connections:
                    if worker_connection.job_event is None:
                        group_manager = self.waiting_groups.pop(0)
                        group_manager.worker_connection = worker_connection
                        asyncio.create_task(group_manager.start_process())
                        return
                print(f"No WORKER FREE | waiting list : {len(self.waiting_groups)}")

    async def enqueue_job(self, group_manager:GroupManager):
        async with self._dispatch_lock:
            if group_manager in self.waiting_groups:
                raise WaitingListError(f"already in waiting list at position {self.waiting_groups.index(group_manager) + 1}")
            self.waiting_groups.append(group_manager)
        await self.dequeue_job()

    # add group manager
    async def add_group_manager(self) -> GroupManager:
        async with self._group_lock:
            manager = GroupManager(self)
            self.group_managers.append(manager)
            print("Active Group Manager: ", len(self.group_managers))
        
        return manager
    
    # remove group manager
    async def remove_group_manager(self, manager: GroupManager):
        async with self._group_lock:
            if manager in self.group_managers:
                self.group_managers.remove(manager)
                print("Group Manager removed: ", len(self.group_managers))
        
        await self._broadcast()

    async def add_worker_connection(self, websocket) -> WorkerConnection:
        async with self._worker_lock:
            connection = WorkerConnection(self, websocket)
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