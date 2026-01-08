from typing import Any, Optional, Union
from enum import Enum
from pydantic import BaseModel

class JobStatus(str, Enum):
    QUEUED = "queued"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    ABORTED = "aborted"

class StatusType(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    SUCCESS = "success"

#############################################################################################

class ServerClientContent(BaseModel):
    job_status: Optional[JobStatus] = None
    queue_position: Optional[int] = None
    worker_num: Optional[int] = None
    group_num: Optional[int] = None
    queue_length: Optional[int] = None

class WorkerServerContent(BaseModel):
    index: int
    response: Optional[str] = None

#############################################################################################

# action to control client from Server
class ServerClientActionType(str, Enum): # server - client
    LOG = "log"
    HEARTBEAT = "heartbeat"

# action to control server from client
class ClientServerActionType(str, Enum): # client - server
    ABORT_REQUEST = "abort_request"
    PROMPT = "prompt"

# action to control python server from worker
class WorkerServerActionType(str, Enum): # worker - server
    LOG = "log"
    END = "end"
    ABORTED = "aborted"
    ERROR = "error"

# action to control worker from python server
class ServerWorkerActionType(str, Enum): # server - worker
    LOG = "log"
    PROMPT = "prompt"
    ABORT_REQUEST = "abort_request"

#############################################################################################

class MessageModel(BaseModel):
    text: str
    status: Optional[StatusType] = StatusType.INFO

class ResponseModel(BaseModel):
    action: Union[ServerClientActionType, ClientServerActionType, ServerWorkerActionType, WorkerServerActionType]
    message: Optional[MessageModel] = None
    content: Optional[Union[ServerClientContent, WorkerServerContent]] = None