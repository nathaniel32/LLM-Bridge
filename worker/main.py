import asyncio
import logging
from worker.setting import config
import websockets
import json
import ssl
import certifi
from common.models import ServerWorkerActionType, StatusType, WorkerServerActionType, StreamResponseContent, MessageModel
from worker.utils import ws_response
import httpx

class Worker:
    def __init__(self, url):
        self.url = url
        self.connection = None
        self.ssl_context = ssl.create_default_context(cafile=certifi.where()) if url.startswith("wss://") else None

    async def send(self, message=None, message_status=StatusType.INFO, content=None, action=WorkerServerActionType.LOG):
        if message:
            message = f"WORKER: {message}"
        message = MessageModel(text=message, status=message_status)
        await ws_response(websocket=self.connection, action=action, message=message, content=content)

    async def prompt(self, prompt):
        OLLAMA_URL = "http://localhost:11434/api/generate"
        MODEL = "gemma3:4b"
        
        payload = {
            "model": MODEL,
            "prompt": prompt,
            "stream": True
        }
        
        await self.send(message=MODEL)
        
        async with httpx.AsyncClient() as client:
            async with client.stream("POST", OLLAMA_URL, json=payload) as response:
                response.raise_for_status()
                
                async for line in response.aiter_lines():
                    if not line:
                        continue
                    
                    data = json.loads(line)
                    
                    if "response" in data:
                        print(data["response"], end="", flush=True)
                        await self.send(action=WorkerServerActionType.STREAM_RESPONSE, content=StreamResponseContent(created_at=data["created_at"], response=data["response"]))
                    
                    if data.get("done", False):
                        print("\n\n--- DONE ---")
                        break

    # server listener
    async def _event_listener(self):
        while True:
            event_data = await self.connection.recv()
            if isinstance(event_data, str):
                data = json.loads(event_data)
                action = data.get("action")
                match action:
                    case ServerWorkerActionType.PROMPT:
                        await self.prompt(prompt=data["content"]["prompt"])
                    case _:
                        await self.send(message="Unknown action", message_status=StatusType.ERROR)

    async def connect(self):
        headers = {"Cookie": f"access_key={config.WORKER_ACCESS_KEY}"}
        try:
            logging.info(f"Connecting to {self.url}...")
            async with websockets.connect(self.url, max_size=2 * 1024 * 1024, additional_headers=headers, ssl=self.ssl_context) as websocket:
                self.connection = websocket
                logging.info("Connected to WebSocket server")
                await self._event_listener()
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