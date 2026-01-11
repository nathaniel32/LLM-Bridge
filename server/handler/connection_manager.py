from server.handler.group_manager import GroupManager
from server.handler.worker_connection import WorkerConnection
from server.handler.client_connection import ClientConnection
from typing import List, Optional
import asyncio
from server.models import RequestError
from common.models import ClientContent, MessageModel, StatusType, GroupCredential

class ConnectionManager:
    def __init__(self):
        self.group_managers: List[GroupManager] = []
        self.client_connections: List[ClientConnection] = []
        self.worker_connections: List[WorkerConnection] = []
        self.waiting_groups: List[GroupManager] = []
        self._group_lock = asyncio.Lock()
        self._worker_lock = asyncio.Lock()
        self._client_lock = asyncio.Lock()
        self._dispatch_lock = asyncio.Lock()

    def _get_groups_credential(self) -> GroupCredential:
        return [gm.group_infos.credential for gm in self.group_managers]
    
    def get_group_by_id(self, group_id) -> GroupManager:
        group = next((g for g in self.group_managers if g.group_infos.credential.id == group_id), None)
        if group is None:
            raise RequestError(f"Group with id {group_id} not found")
        return group

    # send to all clients
    async def broadcast(self, message=None, content=None, action=None):
        async with self._group_lock:
            clients = self.client_connections.copy()
        
        # Lockless broadcast (avoids deadlock)
        for client in clients:
            await client.send(message=message, content=content, action=action)

    async def _notify_queue_position(self, removed_group:Optional[GroupManager]=None):
        for position, group in enumerate(self.waiting_groups):
            position += 1
            group.group_infos.queue_position = position
            await group.send(message=MessageModel(text=f"Your Waiting Position: {position} of {len(self.waiting_groups)}"), content=ClientContent(joined_group_infos=group.group_infos))

        if removed_group is not None and removed_group not in self.waiting_groups:
            removed_group.group_infos.queue_position = 0
            await removed_group.send(content=ClientContent(joined_group_infos=removed_group.group_infos))

    async def remove_from_queue(self, group_manager: GroupManager):
        async with self._dispatch_lock:
            if group_manager in self.waiting_groups:
                self.waiting_groups.remove(group_manager)
                await group_manager.send(message=MessageModel(text="Removed from waiting list", status=StatusType.WARNING))
                await self._notify_queue_position(removed_group=group_manager)
            else:
                await group_manager.send(message=MessageModel(text="Group not found in waiting list", status=StatusType.WARNING))

    async def dequeue_job(self):
        async with self._dispatch_lock:
            if self.waiting_groups:
                for worker_connection in self.worker_connections:
                    if worker_connection.job_event is None:
                        group_manager = self.waiting_groups.pop(0)
                        group_manager.worker_connection = worker_connection
                        asyncio.create_task(group_manager.start_job())
                        await self._notify_queue_position(removed_group=group_manager)
                        return
                print(f"No WORKER FREE | waiting list : {len(self.waiting_groups)}")

    async def enqueue_job(self, group_manager:GroupManager):
        async with self._dispatch_lock:
            if group_manager in self.waiting_groups:
                raise RequestError(f"already in waiting list at position {self.waiting_groups.index(group_manager) + 1}")
            self.waiting_groups.append(group_manager)
            await self._notify_queue_position()
        await self.dequeue_job()

    # add group manager
    async def add_group_manager(self) -> GroupManager:
        async with self._group_lock:
            manager = GroupManager(self)
            self.group_managers.append(manager)
            print("Active Group Manager: ", len(self.group_managers))
        
        await self.broadcast(content=ClientContent(group_num=len(self.group_managers), groups_credential=self._get_groups_credential()))
        return manager
    
    # remove group manager
    async def remove_group_manager(self, manager: GroupManager):
        async with self._group_lock:
            if manager in self.group_managers:
                self.group_managers.remove(manager)
                print("Group Manager removed: ", len(self.group_managers))
        
        await self.broadcast(content=ClientContent(group_num=len(self.group_managers), groups_credential=self._get_groups_credential()))

    async def add_worker_connection(self, websocket) -> WorkerConnection:
        async with self._worker_lock:
            connection = WorkerConnection(self, websocket)
            self.worker_connections.append(connection)
            print("Active worker connection: ", len(self.worker_connections))
        
        await self.broadcast(content=ClientContent(worker_num=len(self.worker_connections)))
        return connection

    async def remove_worker_connection(self, connection: WorkerConnection):
        async with self._worker_lock:
            if connection in self.worker_connections:
                self.worker_connections.remove(connection)
                print("Worker connection removed: ", len(self.worker_connections))
        
        await self.broadcast(content=ClientContent(worker_num=len(self.worker_connections)))

    async def add_client_connection(self, websocket) -> ClientConnection:
        async with self._client_lock:
            connection = ClientConnection(self, websocket)
            self.client_connections.append(connection)
            print("Active Client: ", len(self.client_connections))
        
        await self.broadcast(content=ClientContent(client_num=len(self.client_connections)))
        return connection
    
    async def remove_client_connection(self, connection: ClientConnection):
        async with self._client_lock:
            if connection in self.client_connections:
                self.client_connections.remove(connection)
                print("Client connection removed: ", len(self.client_connections))
        
        await self.broadcast(content=ClientContent(client_num=len(self.client_connections)))