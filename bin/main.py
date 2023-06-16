from enum import Enum, auto
import json
from os import getenv
from typing import Optional
from uuid import UUID, uuid4

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Body, Response, status
from Models.Cores import NotificationMessage, Socket, Connection, Channel, Verbosity
from services import Notifier
from pydantic import BaseModel, Field

load_dotenv()
PORT = int(getenv("NOTIFICATION_CORE_PORT"))

app = FastAPI(title="Varla-Notification-Core")

notifier = Notifier()


# @app.websocket("/bind/{channel_name}")
# async def websocket_endpoint(websocket: WebSocket, channel_name: str):
#     socket = Socket(websocket=websocket, acknowledged=True)
#     print(Connection(websocket=socket))
#     print(uuid4())
#     # await notifier.subscribe(channel_name=channel_name, socket=socket)
#     print(notifier.connections)
#     try:
#         await socket.websocket.send_text(f"Connected!")
#         while True:
#             data = await socket.websocket.receive()
#             print("socket", data)
#             if data["type"] == "websocket.disconnect":
#                 print(socket.websocket, "bye")
#                 notifier.remove(channel_name=channel_name, socket=socket.websocket)
#                 return
#             elif data["text"] == "alive":
#                 socket.acknowledged = True
#             else:
#                 await websocket.send_text(f"Message text was: {data}")
#     except WebSocketDisconnect:
#         notifier.remove(channel_name=channel_name, websocket=socket.websocket)


class subsc(BaseModel):
    connection_id: UUID
    channels: list[Channel]


@app.get("/push/{channel_name}/{message}")
async def push_to_connected_websockets(channel_name: str, message: str):
    await notifier.push(
        NotificationMessage(message=message, channel_names=[channel_name])
    )


@app.post("/push")
async def push_post(message: NotificationMessage):
    await notifier.push(message)


async def bind(connection: Connection):
    await connection.websocket.send_text(
        json.dumps(
            {
                "connection_id": str(connection.id),
                "text": f"Connected, your connection id: {str(connection.id)} ",
            }
        )
    )

    while True:
        data = await connection.websocket.receive()
        print("socket", data)
        if data["type"] == "websocket.disconnect":
            print(connection, "bye")
            notifier.pop(connection_id=connection.id)
            return
        if data["text"] == "alive":
            connection.acknowledged = True
        else:
            await connection.websocket.send_text(f"Message text was: {data}")


@app.websocket("/bind/{channel_name}")
@app.websocket("/connect")
async def connect(websocket: WebSocket, connection_id: Optional[UUID] = None):
    await websocket.accept()
    connection = Connection(websocket=websocket, id=connection_id)
    notifier.connections[connection.id] = connection

    # await subscribe(
    #     channels=[Channel(name="string", verbosity=Verbosity.NORMAL)],
    #     connection_id=connection.id,
    # )
    print(notifier.connections)
    await bind(connection)


@app.websocket("/reconnect/{connection_id}")
async def reconnect(websocket: WebSocket, connection_id: UUID, response: Response):

    if connection_id in notifier.connections:

        await websocket.accept()

        notifier.connections[connection_id].websocket = websocket

        print(notifier.connections)
        await bind(notifier.connections[connection_id])
    else:
        # response.status_code = status.ws
        # await websocket.close(code=status.WS_1001_GOING_AWAY, reason="Invalid ID")

        # return "Unknown connect_id!"

        return await connect(websocket=websocket, connection_id=connection_id)


@app.post("/disconnect")
async def disconnect(connection_id: UUID = Body(embed=True)):
    await notifier.disconnect(connection_id)
    pass


@app.post("/close")
async def close(connection_id: UUID = Body()):
    await notifier.close(connection_id)
    pass


@app.post("/subscribe")
async def subscribe(channels: list[Channel], connection_id: UUID = Body()):
    try:
        await notifier.subscribe(channels, connection_id)
        return "Subscribed!"
    except KeyError:
        return "Unknown connect_id!"


@app.post("/list_subscribtions")
async def list_subscribtions(connection_id: UUID = Body(embed=True)):
    try:
        return notifier.connections[connection_id].channels

    except KeyError:
        return "Unknown connect_id!"


@app.post("/unsubscribe")
async def unsubscribe(channel_names: list[str] = Body(), connection_id: UUID = Body()):
    try:
        await notifier.unsubscribe(
            channel_names=channel_names, connection_id=connection_id
        )
        return "Subscribed!"
    except KeyError:
        return "Unknown connect_id!"
    except Exception as e:
        print(e)


@app.on_event("startup")
async def startup():
    await notifier.generator.asend(None)


if __name__ == "__main__":
    uvicorn.run("main:app", port=PORT, host="0.0.0.0", reload=True)
