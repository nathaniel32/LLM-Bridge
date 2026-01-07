from typing import Any, Optional, Union
from enum import Enum
from pydantic import BaseModel

class JobStatus(str, Enum):
    CREATED = "created"
    FILE_PENDING = "file_pending"
    FILE_RECEIVED = "file_received"
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

# action to control client from Server
class ServerClientActionType(str, Enum): # server - client
    LOG = "log"
    HEARTBEAT = "heartbeat"

# action to control server from client
class ClientServerActionType(str, Enum): # client - server
    ABORT_REQUEST = "abort_request"
    UPLOAD_INIT = "upload_init"
    START_PROCESS = "start_process"

# action to control python server from worker
class WorkerServerActionType(str, Enum): # worker - server
    LOG = "log"
    PROCESS_ERROR = "process_error"
    END_PROCESS = "end_process"
    UPLOAD_RESULT_INIT = "upload_result_init"
    ABORTED = "aborted"

# action to control worker from python server
class ServerWorkerActionType(str, Enum): # server - worker
    LOG = "log"
    SET_JOB = "set_job"
    ABORT_REQUEST = "abort_request"
    UPLOAD_INIT = "upload_init"
    START_PROCESS = "start_process"

class ResponseModel(BaseModel):
    action: Union[ServerClientActionType, ClientServerActionType, ServerWorkerActionType, WorkerServerActionType]
    message: Optional[str] = None
    status_type: Optional[StatusType] = None
    content: Optional[Any] = None   # Union[ClientLogModel, UploadFileModel, JobInfoModel]