import asyncio
from typing import Union

from led_strip.unit import LedStrip
from rpi_ws281x import Color


class LedStripState:
    STATUS_IDLE = 0
    STATUS_VIDEO = 1
    STATUSES = {
        0: "idle",
        1: "video"
    }

    status: int = 0

    led_count: int = 0

    start_brightness: int = 0
    max_brightness: int = 0
    brightness_step: int = 0

    wait_ms: int = 1
    led_step: int = 1

    video_brightness = 255
    idle_brightness = 145
    black_brightness = 0
    idle_brightness_step = 1
    video_brightness_step = 5
    idle_wait_ms = 10
    video_wait_ms = 10

    color_red = 255
    color_green = 116
    color_blue = 0

    strips: dict[str, LedStrip] = {}
    active_animation: Union[asyncio.Task, None] = None


    current_brightness: int = 0
    current_led_num: int = 1
    current_led_count: int = 1
    current_led_step: int = 1
    reverse: bool = False


    def __init__(self, *args, **kwargs):
        self.setattrs(*args, **kwargs)
        for strip in self.strips.values():
            strip.init()

    def setattrs(self, *args, **kwargs):
        self.current_brightness: int = 0
        self.current_led_num: int = 1
        self.current_led_count: int = 1
        self.current_led_step: int = 1
        self.reverse: bool = False

        for fieldName, fieldValue in kwargs.items():
            if hasattr(self, fieldName):
                if fieldName in [
                    "led_count", "brightness_step", "video_led_step",
                    "wait_ms", "start_brightness", "max_brightness",
                    "current_brightness"]:
                    setattr(self, fieldName, int(fieldValue))
                else:
                    setattr(self, fieldName, fieldValue)
            else:
                pass

        self.current_led_num = 0

    async def show(self):
        color = (self.color_red, self.color_green, self.color_blue)

        if self.status == self.STATUS_IDLE:
            if self.current_brightness >= self.max_brightness:
                self.reverse = True
            elif self.current_brightness < self.start_brightness:
                self.reverse = False

            for pixel_num in range(0, self.led_count):
                self.update_all_strips(pixel_num, color, self.current_brightness)

            for strip in self.strips.values():
                strip.show()

            if self.reverse:
                self.current_brightness -= self.brightness_step
            else:
                self.current_brightness += self.brightness_step

        elif self.status == self.STATUS_VIDEO:
            self.current_brightness = self.video_brightness
            if self.current_led_num >= self.led_count:
                await self.clear()
                self.current_led_num = 0

            for i in range(self.current_led_num, self.current_led_num + self.current_led_step,
                           self.current_led_step):
                self.update_all_strips(i, color, self.current_brightness)

                for strip in self.strips.values():
                    strip.show()

            self.current_led_num = self.current_led_num + self.current_led_step

            self.current_brightness += self.brightness_step

        await asyncio.sleep(self.wait_ms / 100000.0)


    def update_all_strips(self, pixel_num: int, color: Color, brightness: int):
        for strip in self.strips.values():
            self.update_strip(strip, pixel_num, color, brightness)

    def update_strip(self, strip: LedStrip, pixel_num: int, color: Color, brightness: int):
        if pixel_num > strip.count:
            return

        strip.strip.setPixelColor(
            pixel_num,
            Color(
                int(brightness / 256 * color[0]),
                int(brightness / 256 * color[1]),
                int(brightness / 256 * color[2])
            )

        )

    async def clear(self):
        for strip in self.strips.values():
            strip.clear()