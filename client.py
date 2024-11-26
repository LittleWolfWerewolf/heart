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
            # if self.status == LEDStripQueue.STATUS_IDLE:
                if IO.input(self.button_pin):
                    print(f'Button released {self.status}')
                elif self.status == LEDStripQueue.STATUS_IDLE:
                        print('Button pressed')
                        await self.led_queue.clear()
                        self.status = LEDStripQueue.STATUS_VIDEO
                await asyncio.sleep(0)

    async def run(self):
        # self.connection_reader, self.connection_writer = await asyncio.open_connection(self.host, self.port)
        # print(f'Connected to {self.host}:{self.port}')


        self.led_queue = LEDStripQueue(self.led_config)
        self.led_queue.init()

        show_led_task = asyncio.create_task(self.show_led())
        get_status_task = asyncio.create_task(self.get_status())
        try:
            await asyncio.gather(show_led_task, get_status_task)
        finally:
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







# Пульсация
# Два режима - IDLE и запущенный рычаг
#
#
# import argparse
# import time
# from rpi_ws281x import PixelStrip, Color
#
# # LED strip configuration:
# LED_COUNT = 300        # Number of LED pixels.
# LED_PIN = 18          # GPIO pin connected to the pixels (18 uses PWM!).
# # LED_PIN = 10        # GPIO pin connected to the pixels (10 uses SPI /dev/spidev0.0).
# LED_FREQ_HZ = 800000  # LED signal frequency in hertz (usually 800khz)
# LED_DMA = 10          # DMA channel to use for generating signal (try 10)
# LED_BRIGHTNESS = 255  # Set to 0 for darkest and 255 for brightest
# LED_INVERT = False    # True to invert the signal (when using NPN transistor level shift)
# LED_CHANNEL = 0       # set to '1' for GPIOs 13, 19, 41, 45 or 53
#
#
# # Define functions which animate LEDs in various ways.
# def colorWipe(strip, color, wait_ms=50):
#     """Wipe color across display a pixel at a time."""
#     for i in range(strip.numPixels()):
#         strip.setPixelColor(i, color)
#         time.sleep(wait_ms / 1000.0)
#
#     strip.show()
#
#
# def theaterChase(strip, color, wait_ms=50, iterations=10):
#     """Movie theater light style chaser animation."""
#     for j in range(iterations):
#         for q in range(3):
#             for i in range(0, strip.numPixels(), 3):
#                 strip.setPixelColor(i + q, color)
#             strip.show()
#             time.sleep(wait_ms / 1000.0)
#             for i in range(0, strip.numPixels(), 3):
#                 strip.setPixelColor(i + q, 0)
#
#
# def wheel(pos):
#     """Generate rainbow colors across 0-255 positions."""
#     if pos < 85:
#         return Color(pos * 3, 255 - pos * 3, 0)
#     elif pos < 170:
#         pos -= 85
#         return Color(255 - pos * 3, 0, pos * 3)
#     else:
#         pos -= 170
#         return Color(0, pos * 3, 255 - pos * 3)
#
#
# def rainbow(strip, wait_ms=20, iterations=1):
#     """Draw rainbow that fades across all pixels at once."""
#     for j in range(256 * iterations):
#         for i in range(strip.numPixels()):
#             strip.setPixelColor(i, wheel((i + j) & 255))
#         strip.show()
#         time.sleep(wait_ms / 1000.0)
#
#
# def rainbowCycle(strip, wait_ms=20, iterations=5):
#     """Draw rainbow that uniformly distributes itself across all pixels."""
#     for j in range(256 * iterations):
#         for i in range(strip.numPixels()):
#             strip.setPixelColor(i, wheel(
#                 (int(i * 256 / strip.numPixels()) + j) & 255))
#         strip.show()
#         time.sleep(wait_ms / 1000.0)
#
#
# def theaterChaseRainbow(strip, wait_ms=50):
#     """Rainbow movie theater light style chaser animation."""
#     for j in range(256):
#         for q in range(3):
#             for i in range(0, strip.numPixels(), 3):
#                 strip.setPixelColor(i + q, wheel((i + j) % 255))
#             strip.show()
#             time.sleep(wait_ms / 1000.0)
#             for i in range(0, strip.numPixels(), 3):
#                 strip.setPixelColor(i + q, 0)
#
#
# if __name__ == '__main__':
#     # Process arguments
#     parser = argparse.ArgumentParser()
#     parser.add_argument('-c', '--clear', action='store_true', help='clear the display on exit')
#     args = parser.parse_args()
#
#     # Create NeoPixel object with appropriate configuration.
#     strip = PixelStrip(LED_COUNT, LED_PIN, LED_FREQ_HZ, LED_DMA, LED_INVERT, LED_BRIGHTNESS, LED_CHANNEL)
#     # Intialize the library (must be called once before other functions).
#     strip.begin()
#
#     print('Press Ctrl-C to quit.')
#     if not args.clear:
#         print('Use "-c" argument to clear LEDs on exit')
#
#     try:
#
#         while True:
#             print('Color wipe animations.')
#             colorWipe(strip, Color(255, 0, 0))  # Red wipe
#             colorWipe(strip, Color(0, 255, 0))  # Green wipe
#             colorWipe(strip, Color(0, 0, 255))  # Blue wipe
#             print('Theater chase animations.')
#             theaterChase(strip, Color(127, 127, 127))  # White theater chase
#             theaterChase(strip, Color(127, 0, 0))  # Red theater chase
#             theaterChase(strip, Color(0, 0, 127))  # Blue theater chase
#             print('Rainbow animations.')
#             rainbow(strip)
#             rainbowCycle(strip)
#             theaterChaseRainbow(strip)
#
#     except KeyboardInterrupt:
#         if args.clear:
#             colorWipe(strip, Color(0, 0, 0), 10)
#
#
