from typing import Optional, Union, List
from enum import Enum
from pydantic import BaseModel, Field
from uuid import uuid4

class GroupStatus(str, Enum):
    ACTIVE = "active"
    DELETED = "deleted"

class InteractionStatus(str, Enum):
    CREATED = "created"
    QUEUED = "queued"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    ABORTED = "aborted"
    DELETED = "deleted"

class StatusType(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    SUCCESS = "success"

#############################################################################################

class AbortException(Exception):
    pass

class Interaction(BaseModel):
    id: str = Field(default_factory=lambda: uuid4().hex)
    status: InteractionStatus = InteractionStatus.CREATED
    prompt: str
    response: str = ""

    def add_response_chunk(self, chunk):
        self.response += chunk
        return self.response

class GroupInfos(BaseModel):
    status: GroupStatus = GroupStatus.ACTIVE
    id: str
    name: str

#############################################################################################

class ResponseStreamContent(BaseModel):
    response: str

class InputJobContent(BaseModel):
    input_id: Optional[str] = None
    input_text: Optional[str] = None

class ClientContent(BaseModel):
    joined_group_id: Optional[str] = None
    interaction: Optional[Interaction] = None
    queue_position: Optional[int] = None
    client_num: Optional[int] = None
    worker_num: Optional[int] = None
    group_num: Optional[int] = None
    groups_infos: Optional[List[GroupInfos]] = None
    queue_length: Optional[int] = None

#############################################################################################

# action to control server from client
class ClientServerActionType(str, Enum): # client - server
    ABORT_INTERACTION = "abort_interaction"
    CREATE_INTERACTION = "create_interaction"
    EDIT_INTERACTION = "edit_interaction"
    DELETE_INTERACTION = "delete_interaction"
    CREATE_GROUP = "create_group"

# action to control client from Server
class ServerClientActionType(str, Enum): # server - client
    HEARTBEAT = "heartbeat"

# action to control worker from python server
class ServerWorkerActionType(str, Enum): # server - worker
    ABORT_INTERACTION = "abort_interaction"
    CREATE_INTERACTION = "create_interaction"

# action to control python server from worker
class WorkerServerActionType(str, Enum): # worker - server
    STREAM_RESPONSE = "stream_response"
    END = "end"
    ABORTED = "aborted"
    ERROR = "error"

#############################################################################################

class MessageModel(BaseModel):
    text: str
    status: StatusType = StatusType.INFO

class ResponseModel(BaseModel):
    action: Optional[Union[ServerClientActionType, ClientServerActionType, ServerWorkerActionType, WorkerServerActionType]] = None
    message: Optional[MessageModel] = None
    content: Optional[Union[ClientContent, InputJobContent, ResponseStreamContent]] = None