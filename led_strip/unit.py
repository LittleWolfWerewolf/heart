import asyncio
import time
from rpi_ws281x import PixelStrip, Color


class LedStrip:
    name = ""

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
    idle_led_step = 1
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
                if fieldName in ["pin", "count", "idle_brightness_step", "video_brightness_step", "video_led_step"]:
                    setattr(self, fieldName, int(fieldValue))
                elif fieldName in ["color_red", "color_green", "color_blue", "idle_wait_ms", "video_wait_ms"]:
                    setattr(self, fieldName, float(fieldValue))
                else:
                    setattr(self, fieldName, fieldValue)

        if self.pin < 1 or self.count < 1:
            raise AttributeError(f"Arguments led pin and led count is required")

        self.channel = 1 if self.pin in [13, 19, 41, 45, 53] else 0
        self.strip = PixelStrip(self.count, self.pin, self.freqz, self.dma, self.invert, 255, self.channel)

    def init(self):
        self.strip.begin()

    def show(self):
        self.strip.show()

    def clear(self):
        for i in range(self.count):
            self.strip.setPixelColor(i, Color(0, 0, 0))
        self.strip.show()
