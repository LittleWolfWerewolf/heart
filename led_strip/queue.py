import asyncio
from configparser import ConfigParser
from typing import Union
from rpi_ws281x import Color
import statistics

from .unit import LedStrip
import configparser


class LEDStripQueue:
    STATUS_IDLE = 0
    STATUS_VIDEO = 1
    STATUSES = {
        0: "idle",
        1: "video"
    }

    config: ConfigParser = configparser.ConfigParser()
    _strips: dict[str, LedStrip] = {}

    active_animation: Union[asyncio.Task, None] = None

    running = False

    debug = False

    def __init__(self, config = None, debug = False):
        if config is None:
            raise AttributeError('Config cannot be null')

        self.config.read(config)

        for section in self.config.sections():
            self.config[section]['name'] = section
            strip = LedStrip(**self.config[section])
            self._strips[strip.name] = strip

        self.debug = debug

    def init(self):
        for strip in self._strips.values():
            strip.init()

        self.running = True
        if self.debug:
            print('LED: LED strip init complete')

    async def run(self, status: int):
        if status not in self.STATUSES.keys():
            raise AttributeError('Invalid status')

        if self.active_animation is None:
            animation_name = self.STATUSES[status]
            if not hasattr(self, animation_name):
                raise AttributeError('Invalid animation name')
            self.active_animation = getattr(self, animation_name)

        await self.active_animation()
        await asyncio.sleep(0)

    async def idle(self, color = None, wait_ms = None, brightness_step = None):
        self.running = True
        if self.debug:
            print('LED: strip start idle')

        settings = self.get_led_settings('idle')
        if wait_ms is not None:
            settings['wait_ms'] = wait_ms

        if color is not None:
            settings['color'] = color

        if brightness_step is not None:
            settings['brightness_step'] = brightness_step

        for strip in self._strips.values():
            strip.start()

        for brightness in range(settings['start_brightness'], settings['max_brightness'], settings['brightness_step']):
            if not self.running:
                return
            if self.debug:
                print(f'LED: Setting brightness: {brightness}')
            await self.set_strips(brightness, settings)

        for brightness in range(settings['max_brightness'], settings['start_brightness'], -settings['brightness_step']):
            if not self.running:
                return
            if self.debug:
                print(f'LED: Setting brightness: {brightness}')
            await self.set_strips(brightness, settings)


    async def video(self, color=None, wait_ms=None, brightness_step=None):
        self.running = True
        if self.debug:
            print('LED: LED strip start video')

        settings = self.get_led_settings('video')
        if wait_ms is not None:
            settings['wait_ms'] = wait_ms

        if color is not None:
            settings['color'] = color

        if brightness_step is not None:
            settings['brightness_step'] = brightness_step

        for strip in self._strips.values():
            strip.start()

        for brightness in range(settings['start_brightness'], settings['max_brightness'], settings['brightness_step']):
            if self.debug:
                print(f'LED: Setting brightness: {brightness}')
            if not self.running:
                return
            await self.set_strips(brightness, settings)

        for brightness in range(settings['max_brightness'], settings['start_brightness'], -settings['brightness_step']):
            if self.debug:
                print(f'LED: Setting brightness: {brightness}')
            if not self.running:
                return
            await self.set_strips(brightness, settings)


    async def set_strips(self, brightness: int, settings: dict):
        for strip in self._strips.values():
            strip.start()

        for led_num in range(1, settings['led_count']):
            for strip in self._strips.values():
                if not self.running:
                    return

                if not strip.running:
                    continue

                if led_num > strip.count:
                    continue

                if 'color' not in settings or settings['color'] is None:
                    color = (strip.color_red, strip.color_green, strip.color_blue)
                else:
                    color = settings['color']

                strip.strip.setPixelColor(
                    led_num,
                    Color(
                        int(brightness / 256 * color[0]),
                        int(brightness / 256 * color[1]),
                        int(brightness / 256 * color[2])
                    )
                )
        for strip in self._strips.values():
            if not self.running:
                return
            strip.strip.show()

        await asyncio.sleep(settings['wait_ms'] / 100000.0)


    def get_led_settings(self, action: str) -> dict:
        if not getattr(list(self._strips.values())[0], f"{action}_brightness") or not getattr(list(self._strips.values())[0], f"{action}_wait_ms"):
            raise AttributeError('Invalid action')

        led_count = max([strip.count for strip in self._strips.values()])
        if action == 'idle':
            start_brightness = min([strip.black_brightness  for strip in self._strips.values()])
        else:
            start_brightness = min([strip.idle_brightness for strip in self._strips.values()])
        max_brightness = max([getattr(strip, f"{action}_brightness") for strip in self._strips.values()])
        brightness_step = statistics.mean([strip.brightness_step for strip in self._strips.values()])
        wait_ms = statistics.mean([getattr(strip, f"{action}_wait_ms") for strip in self._strips.values()])

        result = {
            'led_count': led_count,
            'start_brightness': start_brightness,
            'max_brightness': max_brightness,
            'brightness_step': brightness_step,
            'wait_ms': wait_ms
        }

        if self.debug:
            print(f'LED: Settings: {result}')

        return result


    async def clear(self):
        if self.debug:
            print('LED: Cleared LED strip')
        if self.active_animation is asyncio.Task:
            self.active_animation.cancel()

        for strip in self._strips.values():
            strip.clear()

        self.active_animation = None
        self.running = False