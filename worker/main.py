import asyncio
import logging
import argparse
from common.utils import config

from pathlib import Path
from dotenv import load_dotenv
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(dotenv_path=BASE_DIR / ".env")
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

class Worker:
    def __init__(self, url):
        self.url = url

    async def connect(self):
        print(self.url)

def parse_args():
    parser = argparse.ArgumentParser(description="Worker")

    parser.add_argument(
        "--url",
        type=str,
        help="Server Url"
    )

    return parser.parse_args()

if __name__ == "__main__":
    args = parse_args()
    url = args.url if args.url else config.URL
    worker = Worker(url)
    asyncio.run(worker.connect())