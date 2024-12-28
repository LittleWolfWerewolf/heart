import asyncio
from configparser import ConfigParser
from typing import Union
import statistics

from .state import LedStripState
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

    led_state: LedStripState = None

    active_animation: Union[asyncio.Task, None] = None

    debug = False

    def __init__(self, config = None, debug = False):
        if config is None:
            raise AttributeError('Config cannot be null')

        self.config.read(config)

        strips = {}
        for section in self.config.sections():
            self.config[section]['name'] = section
            strip = LedStrip(**self.config[section])
            strips[strip.name] = strip

        self.led_state = LedStripState(**{"strips":strips})

        self.debug = debug

    def init(self):
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
            self.led_state.status = status

        await self.active_animation()
        await asyncio.sleep(0)

    async def show(self):
        await self.led_state.show()

    async def idle(self, color = None, wait_ms = None, brightness_step = None):
        if self.debug:
            print('LED: strip start idle')

        settings = self.get_led_settings('idle')
        if wait_ms is not None:
            settings['wait_ms'] = wait_ms

        if color is not None:
            settings['color'] = color

        if brightness_step is not None:
            settings['brightness_step'] = brightness_step

        settings['status'] = 0

        self.led_state.setattrs(**settings)

    async def video(self, color=None, wait_ms=None, brightness_step=None):
        if self.debug:
            print('LED: LED strip start video')

        settings = self.get_led_settings('video')
        if wait_ms is not None:
            settings['wait_ms'] = wait_ms

        if color is not None:
            settings['color'] = color

        if brightness_step is not None:
            settings['brightness_step'] = brightness_step
        else:
            settings['brightness_step'] = settings['brightness_step'] * 3

        settings['status'] = 1

        self.led_state.setattrs(**settings)

    def get_led_settings(self, action: str) -> dict:
        for field in ('brightness', 'wait_ms', 'led_step'):
            if not getattr(list(self.led_state.strips.values())[0], f"{action}_{field}"):
                raise AttributeError('Invalid action')

        led_count = max([strip.count for strip in self.led_state.strips.values()])
        if action == 'idle':
            start_brightness = min([strip.black_brightness  for strip in self.led_state.strips.values()])
        else:
            start_brightness = min([strip.idle_brightness for strip in self.led_state.strips.values()]) - 60
        max_brightness = max([getattr(strip, f"{action}_brightness") for strip in self.led_state.strips.values()])
        brightness_step = statistics.mean([getattr(strip, f"{action}_brightness_step") for strip in self.led_state.strips.values()])
        wait_ms = statistics.mean([getattr(strip, f"{action}_wait_ms") for strip in self.led_state.strips.values()])

        led_step = max([strip.video_led_step for strip in self.led_state.strips.values()])

        result = {
            'led_count': led_count,
            'start_brightness': start_brightness,
            'max_brightness': max_brightness,
            'brightness_step': brightness_step,
            'led_step': led_step,
            'wait_ms': wait_ms
        }

        if self.debug:
            print(f'LED: Settings: {result}')

        return result


    async def clear(self):
        if self.debug:
            print('LED: Cleared LED strip')

        await self.led_state.clear()

        self.active_animation = None