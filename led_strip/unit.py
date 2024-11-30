import asyncio
import time
from rpi_ws281x import PixelStrip, Color


class LedStrip:
    name = ""
    running = False

    count = -1
    pin: int = -1
    freqz = 800000  # LED signal frequency in hertz (usually 800khz)
    dma = 10  # DMA channel to use for generating signal (try 10)
    invert = False  # True to invert the signal (when using NPN transistor level shift)
    channel = 0  #set to '1' for GPIOs 13, 19, 41, 45 or 53

    video_brightness = 255
    idle_brightness = 145
    black_brightness = 0
    idle_brightness_step = 1
    video_brightness_step = 5
    idle_wait_ms = 10
    video_wait_ms = 10
    video_led_step = 6

    color_red = 255
    color_green = 116
    color_blue = 0

    strip = None


    def __init__(self, **kwargs):
        for arg in ["name", "count", "pin"]:
            if arg not in kwargs:
                raise AttributeError(f"Argument {arg} is required")

        for fieldName, fieldValue in kwargs.items():
            if hasattr(self, fieldName):
                if fieldName in ["name"]:
                    setattr(self, fieldName, fieldValue)
                elif fieldName in ["pin", "count", "idle_brightness_step", "video_brightness_step", "video_led_step"]:
                    setattr(self, fieldName, int(fieldValue))
                elif fieldName in ["color_red", "color_green", "color_blue", "idle_wait_ms", "video_wait_ms"]:
                    setattr(self, fieldName, float(fieldValue))
                else:
                    setattr(self, fieldName, fieldValue)

        if self.pin < 1 or self.count < 1:
            raise AttributeError(f"Arguments led pin and led count is required")

        self.channel = 1 if self.pin in [13, 19, 41, 45, 53] else 0
        self.strip = PixelStrip(self.count, self.pin, self.freqz, self.dma, self.invert, self.video_brightness, self.channel)

    def init(self):
        self.strip.begin()
        self.running = True

    def start(self):
        self.running = True

    def clear(self):
        self.running = False
        for i in range(self.count):
            self.strip.setPixelColor(i, Color(0, 0, 0))
        self.strip.show()

    async def show_idle_animation(self, color = None, wait_ms = None, brightness_step = None):
        if wait_ms is None:
            wait_ms = self.idle_wait_ms

        await self.show_pulse_animation(
            start_brightness = self.black_brightness,
            stop_brightness=self.idle_brightness,
            color=color,
            wait_ms=wait_ms,
            brightness_step=brightness_step
        )
        # await asyncio.sleep(0)

    async def show_active_animation(self, color = None, wait_ms = None, brightness_step = None):
        if wait_ms is None:
            wait_ms = self.active_wait_ms

        await self.show_pulse_animation(
            start_brightness = self.idle_brightness,
            stop_brightness=self.active_brightness,
            color=color,
            wait_ms=wait_ms,
            brightness_step=brightness_step
        )
        await asyncio.sleep(0)

    async def show_pulse_animation(self, start_brightness, stop_brightness, color = None, wait_ms = None, brightness_step = None):
        if brightness_step is None:
            brightness_step = self.brightness_step

        for i in range(start_brightness, stop_brightness, brightness_step):
            if not self.running:
                return
            await self._setstrip(color=color, wait_ms=wait_ms, brightness=i)
            # await asyncio.sleep(0)


        for i in range(stop_brightness, start_brightness, -brightness_step):
            if not self.running:
                return
            await self._setstrip(color=color, wait_ms=wait_ms, brightness=i)
            # await asyncio.sleep(0)

    async def _setstrip(self, color = None, wait_ms = None, brightness = None):
        if color is None:
            color = (self.color_red, self.color_green, self.color_blue)

        if not self.running:
            return

        for led_num in range(1, self.count):
            self.strip.setPixelColor(
                led_num,
                Color(
                    int(brightness / 256 * color[0]),
                    int(brightness / 256 * color[1]),
                    int(brightness / 256 * color[2])
                )
            )
        self.strip.show()
        # await asyncio.sleep(wait_ms / 100000.0)
        time.sleep(wait_ms / 100000.0)
