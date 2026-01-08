import asyncio
import logging
import argparse
from worker.setting import config

class Worker:
    def __init__(self, url):
        self.url = url

    async def connect(self):
        logging.info(self.url)

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