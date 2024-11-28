#!/usr/bin/env python3

import os
import asyncio
from configparser import ConfigParser

import RPi.GPIO as IO

from led_strip.queue import LEDStripQueue


class Client:
    config = ConfigParser()
    led_config: ConfigParser = None
    led_queue: LEDStripQueue = None

    host: str = None
    port: int = None

    connection_writer: asyncio.StreamWriter = None
    connection_reader: asyncio.StreamReader = None

    button_pin = 0

    status: int = -1
    server_started: bool = False

    def __init__(self, server_config = None, led_config = None):
        if server_config is None:
            raise AttributeError('Server config cannot be null')
        if led_config is None:
            raise AttributeError('LED config cannot be null')

        self.config.read(server_config)

        if 'server' not in self.config.sections():
            raise AttributeError('Server section cannot be null')

        for key in ['host', 'port']:
            if key not in self.config['server']:
                raise AttributeError('Server section must contain key "%s"' % key)

        for field in self.config['server']:
            if hasattr(self, field):
                setattr(self, field, self.config['server'][field])

        if 'button' not in self.config.sections() or 'pin' not in self.config['button']:
            raise AttributeError('Button pin cannot be null')

        self.button_pin = int(self.config['button']['pin'])
        IO.setup(self.button_pin, IO.IN)

        self.led_config = led_config
        self.status = LEDStripQueue.STATUS_IDLE

    async def show_led(self):
        try:
            while True:
                await self.led_queue.run(self.status)
                await asyncio.sleep(0)
        finally:
            await self.led_queue.clear()

    async def get_status(self):
        while True:
            if IO.input(self.button_pin) < 1 and not self.server_started:
                if self.status == LEDStripQueue.STATUS_IDLE:
                    await self.led_queue.clear()
                    self.status = LEDStripQueue.STATUS_VIDEO
                    self.server_started = True
                    await self.send_status_to_server()
                # else:
                    # print(f'Button released {self.status}')

                await asyncio.sleep(0)
            else:
                if IO.input(self.button_pin) > 0 and not self.server_started:
                    self.status = LEDStripQueue.STATUS_IDLE
                await asyncio.sleep(0)

    async def connect_to_server(self):
        try:
            self.connection_reader, self.connection_writer = await asyncio.open_connection(self.host, self.port)
            print(f'Connected to {self.host}:{self.port}')
        except ConnectionRefusedError as e:
            print(f'Connection not established with status {e}')
            return

        while True:
            data = await self.connection_reader.read(100)
            try:
                self.status = int(data.decode().strip())
            except ValueError:
                self.connection_writer.write('Invalid int argument\n'.encode())
                continue
            except Exception as e:
                self.connection_writer.write(f'Invalid status {e}\n'.encode())
                continue

            if self.status not in LEDStripQueue.STATUSES.keys():
                self.connection_writer.write(f'Invalid status number!'.encode())

            if self.status == LEDStripQueue.STATUS_IDLE:
                self.server_started = False

            await asyncio.sleep(0)

    async def send_status_to_server(self):
        if self.connection_writer is not None:
            try:
                self.connection_writer.write(str(self.status).encode())
            except Exception as e:
                pass
            await self.connection_writer.drain()

    async def run(self):
        self.led_queue = LEDStripQueue(self.led_config)
        self.led_queue.init()

        show_led_task = asyncio.create_task(self.show_led())
        get_status_task = asyncio.create_task(self.get_status())
        connect_to_server_task = asyncio.create_task(self.connect_to_server())
        try:
            await asyncio.gather(show_led_task, get_status_task, connect_to_server_task)
        finally:
            self.connection_writer.close()
            await self.led_queue.clear()


if __name__ == "__main__":
    IO.setwarnings(False)
    IO.setmode(IO.BCM)

    client = Client(
        server_config=f"{os.getcwd()}/server.ini",
        led_config=f"{os.getcwd()}/led.ini"
    )
    try:
        asyncio.run(client.run())
    except KeyboardInterrupt:
        asyncio.run(client.led_queue.clear())
        print('All strips are cleared successfully')
    finally:
        asyncio.new_event_loop()
