from typing import Optional, Union
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

class OllamaMessageContent(BaseModel):
    role: str
    content: str

class OllamaChatResponse(BaseModel):
    model: str
    created_at: str
    message: OllamaMessageContent
    done: bool
    done_reason: Optional[str] = None
    total_duration: Optional[int] = None
    load_duration: Optional[int] = None
    prompt_eval_count: Optional[int] = None
    prompt_eval_duration: Optional[int] = None
    eval_count: Optional[int] = None
    eval_duration: Optional[int] = None

class CreateJobContent(BaseModel):
    text_input: str

class ClientContent(BaseModel):
    job_status: Optional[JobStatus] = None
    prompt: Optional[str] = None
    response: Optional[str] = None
    response_stream: Optional[OllamaChatResponse] = None
    queue_position: Optional[int] = None
    worker_num: Optional[int] = None
    group_num: Optional[int] = None
    queue_length: Optional[int] = None

#############################################################################################

# action to control server from client
class ClientServerActionType(str, Enum): # client - server
    ABORT_REQUEST = "abort_request"
    CREATE_JOB = "create_job"

# action to control client from Server
class ServerClientActionType(str, Enum): # server - client
    HEARTBEAT = "heartbeat"

# action to control worker from python server
class ServerWorkerActionType(str, Enum): # server - worker
    ABORT_REQUEST = "abort_request"
    CREATE_JOB = "create_job"

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
    content: Optional[Union[ClientContent, CreateJobContent, OllamaChatResponse]] = None