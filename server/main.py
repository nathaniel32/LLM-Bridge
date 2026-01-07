from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from server.routes.connection import Connection
from common.utils import config
import logging

from pathlib import Path
from dotenv import load_dotenv
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(dotenv_path=BASE_DIR / ".env")
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

class App:
    def __init__(self):
        self.app = FastAPI()
        self.setup_middleware()
        self.app.include_router(Connection().router)

    def setup_middleware(self):
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    def get_app(self):
        return self.app

app = App().get_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(App().get_app(), host="0.0.0.0", port=9050)