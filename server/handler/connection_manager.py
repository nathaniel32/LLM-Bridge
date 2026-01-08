from server.handler.group_connection import GroupConnection
from server.handler.worker_connection import WorkerConnection
from typing import List
import asyncio

class ConnectionManager:
    def __init__(self):
        self.group_sessions: List[GroupConnection] = []
        self.worker_sessions: List[WorkerConnection] = []
        self.waiting_groups: List[GroupConnection] = []
        self._group_lock = asyncio.Lock()
        self._worker_lock = asyncio.Lock()
        self._dispatch_lock = asyncio.Lock()

    # send to all groups
    async def _broadcast(self):
        async with self._group_lock:
            groups = self.group_sessions.copy()
        
        # Lockless broadcast (avoids deadlock)
        for group_session in groups:
            print(group_session)

    # add group session
    async def add_group_session(self) -> GroupConnection:
        async with self._group_lock:
            session = GroupConnection(self)
            self.group_sessions.append(session)
            print("Active Group session: ", len(self.group_sessions))
        
        return session
    
    # remove group session
    async def remove_group_session(self, session: GroupConnection):
        async with self._group_lock:
            if session in self.group_sessions:
                self.group_sessions.remove(session)
                print("Group session removed: ", len(self.group_sessions))
        
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