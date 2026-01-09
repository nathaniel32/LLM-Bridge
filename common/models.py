from typing import Optional, Union
from enum import Enum
from pydantic import BaseModel, Field
from uuid import uuid4

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

class Interaction(BaseModel):
    id: str = Field(default_factory=lambda: uuid4().hex)
    prompt: str
    response: str = ""

    def add_response_chunk(self, chunk):
        self.response += chunk
        return self.response

#############################################################################################

class ResponseStreamContent(BaseModel):
    response: str

class InputJobContent(BaseModel):
    input_id: Optional[str] = None
    input_text: str

class ClientContent(BaseModel):
    job_status: Optional[JobStatus] = None
    interaction: Optional[Interaction] = None
    queue_position: Optional[int] = None
    worker_num: Optional[int] = None
    group_num: Optional[int] = None
    queue_length: Optional[int] = None

#############################################################################################

# action to control server from client
class ClientServerActionType(str, Enum): # client - server
    ABORT_JOB = "abort_job"
    CREATE_JOB = "create_job"
    EDIT_JOB = "edit_job"

# action to control client from Server
class ServerClientActionType(str, Enum): # server - client
    HEARTBEAT = "heartbeat"

# action to control worker from python server
class ServerWorkerActionType(str, Enum): # server - worker
    ABORT_JOB = "abort_job"
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
    content: Optional[Union[ClientContent, InputJobContent, ResponseStreamContent]] = None