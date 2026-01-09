import asyncio
import logging
from worker.setting import config
import websockets
import json
import ssl
import certifi
from common.models import ServerWorkerActionType, StatusType, WorkerServerActionType, MessageModel, ResponseModel, ResponseStreamContent
from worker.utils import ws_response
import httpx
from pydantic import BaseModel
from typing import Optional

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

class Worker:
    def __init__(self, url):
        self.url = url
        self.connection = None
        self.ssl_context = ssl.create_default_context(cafile=certifi.where()) if url.startswith("wss://") else None

    async def send(self, message:MessageModel=None, content=None, action=None):
        if message:
            message.text = f"WORKER: {message.text}"
        await ws_response(websocket=self.connection, action=action, message=message, content=content)

    async def stream_chat(self, messages):
        OLLAMA_URL = "http://localhost:11434/api/chat"
        MODEL = "gemma3:4b"
        
        payload = {
            "model": MODEL,
            "messages": messages,
            "stream": True
        }
        
        await self.send(message=MessageModel(text=MODEL))
        
        try:
            print("\n\n==== INPUT:", messages)
            async with httpx.AsyncClient() as client:
                async with client.stream("POST", OLLAMA_URL, json=payload) as response:
                    print("====AI:")

                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if not line:
                            continue
                        data = json.loads(line)                        
                        ollama_response = OllamaChatResponse(**data)
                        
                        if ollama_response.message.content:
                            print(ollama_response.message.content, end="", flush=True)
                            await self.send(action=WorkerServerActionType.STREAM_RESPONSE, content=ResponseStreamContent(response=ollama_response.message.content))
                        if ollama_response.done:
                            break
        except Exception as e:
            logging.exception(f"Exception: {e}")
            await self.send(message=MessageModel(text=str(e)), action=WorkerServerActionType.ERROR)
        finally:
            print("\nEND!")
            await self.send(action=WorkerServerActionType.END)


    # server listener
    async def _event_listener(self):
        current_task = None

        while True:
            event_data = await self.connection.recv()
            if isinstance(event_data, str):
                response_model = ResponseModel(**json.loads(event_data))
                match response_model.action:
                    case ServerWorkerActionType.CREATE_JOB:
                        messages = json.loads(response_model.content.input_text)
                        current_task = asyncio.create_task(self.stream_chat(messages=messages))
                    case ServerWorkerActionType.ABORT_JOB:
                        await self.send(action=WorkerServerActionType.ABORTED)
                        current_task.cancel()
                    case _:
                        await self.send(message=MessageModel(text="Unknown action", status=StatusType.ERROR))

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
            logging.exception(f"Exception: {e}")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Worker")
    parser.add_argument("--url", type=str, help="Server Url")
    args = parser.parse_args()

    url = args.url if args.url else config.URL
    worker = Worker(url)
    asyncio.run(worker.connect())