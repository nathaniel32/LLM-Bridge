import asyncio
import logging
from worker.setting import config
import websockets
import json
import ssl
import certifi
from common.models import ServerWorkerActionType, StatusType, WorkerServerActionType
from worker.utils import ws_response

class Worker:
    def __init__(self, url):
        self.url = url
        self.connection = None
        self.ssl_context = ssl.create_default_context(cafile=certifi.where()) if url.startswith("wss://") else None

    async def send(self, message=None, message_status=StatusType.INFO, content=None, action=WorkerServerActionType.LOG):
        if message:
            message = f"WORKER: {message}"
        await ws_response(websocket=self.connection, action=action, message=message, message_status=message_status, content=content)

    # server listener
    async def _message_listener(self):
        while True:
            message = await self.connection.recv()
            if isinstance(message, str):
                data = json.loads(message)
                action = data.get("action")
                match action:
                    case ServerWorkerActionType.PROMPT:
                        print(data)
                        await self.send(message=data)
                    case _:
                        await self.send(message="Unknown action", message_status=StatusType.ERROR)

    async def connect(self):
        headers = {"Cookie": f"access_key={config.WORKER_ACCESS_KEY}"}
        try:
            logging.info(f"Connecting to {self.url}...")
            async with websockets.connect(self.url, max_size=2 * 1024 * 1024, additional_headers=headers, ssl=self.ssl_context) as websocket:
                self.connection = websocket
                logging.info("Connected to WebSocket server")
                await self._message_listener()
        except websockets.ConnectionClosed as e:
            if e.code == 1008:
                logging.error(f"Unauthorized")
                return
            logging.warning("WebSocket connection was closed")
        except Exception as e:
            logging.error(f"Exception: {e}")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Worker")
    parser.add_argument("--url", type=str, help="Server Url")
    args = parser.parse_args()

    url = args.url if args.url else config.URL
    worker = Worker(url)
    asyncio.run(worker.connect())