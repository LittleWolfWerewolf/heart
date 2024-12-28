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
    server_connected: bool = False
    led_cleared: bool = True

    status_changed: bool = False
    button_state: bool = False

    led_debug: bool = False
    server_debug: bool = False

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

        if 'service' in self.config.sections() and 'debug' in self.config['service']:
            self.led_debug = True if int(self.config['service']['debug']) > 0 else False

        if 'debug' in self.config['server']:
            self.debug = True if int(self.config['server']['debug']) > 0 else False

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
            await asyncio.sleep(0)

    async def connect_to_server(self):
        try:
            self.connection_reader, self.connection_writer = await asyncio.open_connection(self.host, self.port)
            self.server_connected = True
            if self.debug:
                print(f'Connected to {self.host}:{self.port}')
        except ConnectionRefusedError as e:
            print(f'Connection not established with status {e}')
            return
        except OSError as e:
            print(f'Connection not established with status {e}')
            return

        while True:
            data = await self.connection_reader.read(100)
            try:
                status = int(data.decode().strip())
            except ValueError:
                self.connection_writer.write('Invalid int argument\n'.encode())
                continue
            except Exception as e:
                self.connection_writer.write(f'Invalid status {e}\n'.encode())
                continue

            if status not in LEDStripQueue.STATUSES.keys():
                self.connection_writer.write(f'Invalid status number!'.encode())
                continue

            if status == LEDStripQueue.STATUS_IDLE:
                if self.server_connected:
                    if self.debug:
                        print('SERVER: Stop video')
                    self.server_started = False
                else:
                    if self.debug:
                        print('LOCAL: Stop video')
                    self.status = status
            else:
                if self.debug:
                    print(f'SERVER: Set status {status}')
                self.status = status

            await asyncio.sleep(0)

    async def send_status_to_server(self):
        if self.connection_writer is not None and self.server_connected:
            try:
                self.connection_writer.write(str(self.status).encode())
                if self.debug:
                    print('SERVER: Send start to server')
            except Exception as e:
                pass
            await self.connection_writer.drain()

    async def get_status(self):
        while True:
            # button pressed
            if (IO.input(self.button_pin) < 1):
                if self.server_connected:
                    if not self.server_started and self.status == LEDStripQueue.STATUS_IDLE and self.led_cleared:
                        if self.debug:
                            print('SERVER: Start video')
                        self.server_started = True
                        self.led_cleared = False
                        await self.led_queue.clear()
                        self.status = LEDStripQueue.STATUS_VIDEO
                        self.status_changed = True
                        await self.send_status_to_server()
                    elif not self.server_started and not self.led_cleared:
                        if self.debug:
                            print('SERVER: Stop video')
                        if self.status != LEDStripQueue.STATUS_IDLE:
                            await self.led_queue.clear()
                            self.status_changed = True
                        self.status = LEDStripQueue.STATUS_IDLE

                else:
                    if self.debug:
                        print('LOCAL: Start video')
                    if self.status == LEDStripQueue.STATUS_IDLE:
                        await self.led_queue.clear()
                    self.status = LEDStripQueue.STATUS_VIDEO
                    if not self.button_state:
                        self.status_changed = True
                        self.button_state = True

            else:
                if self.server_connected:
                    if self.status != LEDStripQueue.STATUS_IDLE:
                        if not self.server_started:
                            if self.debug:
                                print('SERVER: Start idle')
                            await self.led_queue.clear()
                            self.status = LEDStripQueue.STATUS_IDLE
                            self.status_changed = True
                            self.led_cleared = True
                    else:
                        if self.debug:
                            print('SERVER: reload')
                        self.led_cleared = True

                else:
                    if self.debug:
                        print('LOCAL: reload')
                    if self.status != LEDStripQueue.STATUS_IDLE:
                        await self.led_queue.clear()
                    self.status = LEDStripQueue.STATUS_IDLE
                    if self.button_state:
                        self.status_changed = True
                        self.button_state = False

            if self.status_changed:
                await self.led_queue.clear()
                await self.led_queue.run(self.status)
                self.status_changed = False

            await self.led_queue.show()
            await asyncio.sleep(0)

    async def run(self):
        self.led_queue = LEDStripQueue(self.led_config, self.led_debug)
        self.led_queue.init()
        await self.led_queue.run(LEDStripQueue.STATUS_IDLE)

        # show_led_task = asyncio.create_task(self.show_led())
        get_status_task = asyncio.create_task(self.get_status())
        connect_to_server_task = asyncio.create_task(self.connect_to_server())
        try:
            # await asyncio.gather(show_led_task, get_status_task, connect_to_server_task)
            await asyncio.gather(get_status_task, connect_to_server_task)
        finally:
            if self.server_connected:
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
