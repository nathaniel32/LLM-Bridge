from fastapi import APIRouter, WebSocket, status
from common.utils import config

class Connection:
    def __init__(self):
        self.router = APIRouter(prefix="/connection", tags=["Connection"])