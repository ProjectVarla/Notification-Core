# From https://gist.github.com/francbartoli/2532f8bd8249a4cefa32f9c17c886a4b
# From https://github.com/tiangolo/fastapi/issues/258

from enum import Enum, auto
import json
from typing import List
from uuid import UUID
from starlette.websockets import WebSocket

from Models.Cores import NotificationMessage, Socket, Connection, Channel, Verbosity


class Notifier:
    def __init__(self):

        self.connections: dict[UUID, List[Connection]] = {}
        self.channels: dict[str, List[UUID]] = {}

        self.generator = self.get_notification_generator()

    async def get_notification_generator(self):
        while True:
            message = yield
            await self._notify(message=message)

    async def _notify(self, message: NotificationMessage):
        anti_spam_list = []
        print("HIIIIIIIIIIIIIIIIII")
        for channel_name in message.channel_names:
            if channel_name not in self.channels:
                continue
            for connection_id in self.channels[channel_name]:
                try:
                    if (
                        connection_id not in anti_spam_list
                        and self.connections[connection_id].websocket
                    ):
                        await self.connections[connection_id].websocket.send_text(
                            json.dumps({"text": message.message, "from": channel_name})
                        )
                        anti_spam_list.append(connection_id)
                except Exception as e:
                    print("broken", self.connections[connection_id].websocket, e)
                    await self.disconnect(connection_id=connection_id)

    async def send(self, connection_id: UUID, message: dict):
        await self.connections[connection_id].websocket.send_text(json.dumps(message))

    async def push(self, message: NotificationMessage):
        await self.generator.asend((message))

    async def subscribe(self, channels: list[Channel], connection_id: UUID):
        for channel in channels:
            if channel.name not in self.channels:
                self.channels[channel.name] = []

            self.channels[channel.name].append(connection_id)
            self.connections[connection_id].channels.append(channel)

            await self.send(
                connection_id,
                message={
                    "from": channel.name,
                    "text": f"Subscribed!",
                },
            )

    async def unsubscribe(self, channel_names: list[str], connection_id: UUID):

        for channel_name in channel_names:

            if (
                channel_name in self.channels
                and connection_id in self.channels[channel_name]
            ):

                self.channels[channel_name].remove(connection_id)

                self.connections[connection_id].channels = [
                    channel
                    for channel in self.connections[connection_id].channels
                    if channel.name != channel_name
                ]

                await self.send(
                    connection_id,
                    message={
                        "from": channel_name,
                        "text": f"Unsubscribed!",
                    },
                )

    def pop(self, connection_id: UUID) -> WebSocket:
        socket: WebSocket = self.connections[connection_id].websocket
        self.connections[connection_id].websocket = None
        return socket

    async def disconnect(self, connection_id: UUID):
        try:
            socket: WebSocket = self.pop(connection_id)

            if socket:
                await socket.close()

            print(self.connections)

        except Exception as e:
            print(e)
            print(self.connections)

    async def close(self, connection_id: UUID):
        try:
            self.connections.pop(connection_id)

        except Exception as e:
            print(e)
            print(self.connections)
            # raise e

    # async def close_all(self):
    #     for channel in self.connections:
    #         while len(self.connections[channel]) > 0:
    #             socket = self.connections[channel].pop()
    #             await self.close(socket)

    # async def close(self, socket: Socket):
    #     await socket.websocket.close()
