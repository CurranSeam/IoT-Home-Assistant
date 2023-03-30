import asyncio
import websockets

from application import app
from application.services import svc_common, security as vault

def start():
    host = vault.get_value("APP", "config", "host")
    port = vault.get_value("SOCKETS", "stats", "port")

    start_server = websockets.serve(send_stats, host, port)

    asyncio.get_event_loop().run_until_complete(start_server)

async def send_stats(websocket, path):
    while True:
        stats = svc_common.get_server_stats()

        await websocket.send(stats)
        await asyncio.sleep(0.1)
