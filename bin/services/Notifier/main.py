# From https://gist.github.com/francbartoli/2532f8bd8249a4cefa32f9c17c886a4b
# From https://github.com/tiangolo/fastapi/issues/258

from typing import List

from Models.Cores import NotificationMessage, Socket


class Notifier:
    def __init__(self):
        self.connections: dict[str, List[Socket]] = {}
        self.generator = self.get_notification_generator()

    async def get_notification_generator(self):
        while True:
            message, channel_name = yield
            await self._notify(channel_name=channel_name, message=message)

    async def push(self, message: NotificationMessage):
        await self.generator.asend((message.message, message.channel_name))
        print(self.connections)

    async def subscribe(self, channel_name: str, socket: Socket):
        await socket.websocket.accept()

        if channel_name not in self.connections:
            self.connections[channel_name] = []

        self.connections[channel_name].append(socket)

    def remove(self, channel_name: str, socket: Socket):
        print(self.connections)
        try:
            socket.acknowledged = True
            self.connections[channel_name].remove(socket)
        except:
            print(self.connections)
            print("ya zeft")

    async def close_all(self):
        for channel in self.connections:
            while len(self.connections[channel]) > 0:
                socket = self.connections[channel].pop()
                await self.close(socket)

    async def close(self, socket: Socket):
        await socket.websocket.close()

    async def _notify(self, channel_name: str, message: str):
        living_connections = []
        while (
            channel_name in self.connections and len(self.connections[channel_name]) > 0
        ):
            socket = self.connections[channel_name].pop()

            # if socket.acknowledged:
            socket.acknowledged = False
            try:
                living_connections.append(socket)
                await socket.websocket.send_text(message)
            except:
                print("broken", socket)
                self.remove(channel_name, socket)
            # else: await self.close(socket)

        self.connections[channel_name] = living_connections
