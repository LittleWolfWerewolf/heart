import asyncio
from configparser import ConfigParser
from typing import Union
import threading

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

    def __init__(self, config = None):
        if config is None:
            raise AttributeError('Config cannot be null')

        self.config.read(config)

        for section in self.config.sections():
            self.config[section]['name'] = section
            strip = LedStrip(**self.config[section])
            self._strips[strip.name] = strip

    def init(self):
        for strip in self._strips.values():
            strip.init()

        self.running = True

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
        for strip in self._strips.values():
            strip.start()
            await strip.show_idle_animation(color=color, wait_ms=wait_ms, brightness_step=brightness_step)
        await asyncio.sleep(0)

    async def video(self, color = None, wait_ms = None, brightness_step = None):
        self.running = True
        for strip in self._strips.values():
            strip.start()
            await strip.show_active_animation(color=color, wait_ms=wait_ms, brightness_step=brightness_step)
        await asyncio.sleep(0)

    async def clear(self):
        if self.active_animation is asyncio.Task:
            self.active_animation.cancel()

        for strip in self._strips.values():
            strip.clear()

        self.active_animation = None
        self.running = False