from fastapi import APIRouter, Request
from fastapi.responses import FileResponse
import os
from server.setting import BASE_DIR

class Frontend:
    def __init__(self):
        self.router = APIRouter(tags=["Frontend"])
        self.router.add_api_route("/", self.root, methods=["GET"])

    async def root(self, request: Request):
        return FileResponse(os.path.join(BASE_DIR, ".frontend", "index.html"))