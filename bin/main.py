from os import getenv

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from Models.Cores import NotificationMessage, Socket
from services import Notifier

load_dotenv()
PORT = int(getenv("NOTIFICATION_CORE_PORT"))

app = FastAPI(title="Varla-Notification-Core")

notifier = Notifier()


@app.websocket("/bind/{channel_name}")
async def websocket_endpoint(websocket: WebSocket, channel_name: str):
    socket = Socket(websocket=websocket, acknowledged=True)
    await notifier.subscribe(channel_name=channel_name, socket=socket)
    print(notifier.connections)
    try:
        await socket.websocket.send_text(f"Connected!")
        while True:
            data = await socket.websocket.receive()
            print("socket", data)
            if data["type"] == "websocket.disconnect":
                print(socket.websocket, "bye")
                notifier.remove(channel_name=channel_name, socket=socket.websocket)
                return
            elif data["text"] == "alive":
                socket.acknowledged = True
            else:
                await websocket.send_text(f"Message text was: {data}")
    except WebSocketDisconnect:
        notifier.remove(channel_name=channel_name, websocket=socket.websocket)


@app.get("/push/{channel_name}/{message}")
async def push_to_connected_websockets(channel_name: str, message: str):
    await notifier.push(NotificationMessage(message=message, channel_name=channel_name))


@app.post("/push")
async def push_post(message: NotificationMessage):
    await notifier.push(message)


@app.on_event("startup")
async def startup():
    await notifier.generator.asend(None)


if __name__ == "__main__":
    uvicorn.run("main:app", port=PORT, host="0.0.0.0")
