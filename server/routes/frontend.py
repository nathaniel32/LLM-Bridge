from fastapi import APIRouter, status, Request
from fastapi.responses import HTMLResponse, FileResponse
import os

class Frontend:
    def __init__(self):
        self.router = APIRouter(tags=["Frontend"])
        self.router.add_api_route("/", self.root, methods=["GET"])

    async def root(self, request: Request):
        return FileResponse(os.path.join(".frontend", "index.html"))