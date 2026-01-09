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

class StreamResponseContent(BaseModel):
    created_at: str
    response: str

class PromptContent(BaseModel):
    prompt: str

class ClientContent(BaseModel):
    job_status: Optional[JobStatus] = None
    response: Optional[str] = None
    response_chunk: Optional[StreamResponseContent] = None
    queue_position: Optional[int] = None
    worker_num: Optional[int] = None
    group_num: Optional[int] = None
    queue_length: Optional[int] = None

#############################################################################################

# action to control server from client
class ClientServerActionType(str, Enum): # client - server
    ABORT_REQUEST = "abort_request"
    PROMPT = "prompt"

# action to control client from Server
class ServerClientActionType(str, Enum): # server - client
    LOG = "log"
    HEARTBEAT = "heartbeat"

# action to control worker from python server
class ServerWorkerActionType(str, Enum): # server - worker
    LOG = "log"
    ABORT_REQUEST = "abort_request"
    PROMPT = "prompt"

# action to control python server from worker
class WorkerServerActionType(str, Enum): # worker - server
    LOG = "log"
    STREAM_RESPONSE = "stream_response"
    END = "end"
    ABORTED = "aborted"
    ERROR = "error"

#############################################################################################

class MessageModel(BaseModel):
    text: str
    status: StatusType = StatusType.INFO

class ResponseModel(BaseModel):
    action: Union[ServerClientActionType, ClientServerActionType, ServerWorkerActionType, WorkerServerActionType]
    message: Optional[MessageModel] = None
    content: Optional[Union[ClientContent, PromptContent, StreamResponseContent]] = None