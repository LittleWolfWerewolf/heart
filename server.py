#!/usr/bin/env python3

import asyncio
import os
import random
from configparser import ConfigParser

class Server:
    config: ConfigParser = None
    writer: asyncio.StreamWriter = None

    def __init__(self, config: str):
        if config is None:
            raise AttributeError('Server config cannot be null')

        self.config = ConfigParser()
        self.config.read(config)

        if 'server' not in self.config.sections():
            raise AttributeError('Server section cannot be null')

        if 'port' not in self.config['server']:
            raise AttributeError('Server section must contain key "port"')

    async def handle_echo(self, reader, writer):
        self.writer = writer
        while True:
            data = await reader.read(100)
            try:
                message = int(data.decode().strip())
            except ValueError:
                self.writer.write('Invalid int argument\n')
                self.writer.close()

            addr = self.writer.get_extra_info('peername')

            print(f"Received {message!r} from {addr!r}")

            sleep_time = random.randint(3, 10)
            print(f"Sleeping {sleep_time} seconds...")
            await asyncio.sleep(sleep_time)

            print(f"Send: {message!r}")
            self.writer.write("0".encode())
            await self.writer.drain()

async def main(server):
    server_task = await asyncio.start_server(
        server.handle_echo, server.config['server']['host'], int(server.config['server']['port']))

    addr = server_task.sockets[0].getsockname()
    print(f'Serving on {addr}')

    async with server_task:
        await server_task.serve_forever()

if __name__ == '__main__':
    server = Server(f"{os.getcwd()}/server.ini")
    try:
        asyncio.run(main(server))
    except KeyboardInterrupt:
        asyncio.new_event_loop()