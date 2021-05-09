import time
from luma.core.render import canvas
import RPi.GPIO as GPIO
from luma.core.interface.serial import bitbang
from luma.oled.device import ssd1322

from tests.BaseTest import BaseTest
from gpiodefs import *
import sys

class Test(BaseTest):
    def __init__(self, short8="precursors/short_8khz.wav",
                 long8="precursors/long_8khz.wav"):
        BaseTest.__init__(self, name="Audio Clips", shortname="AudWAV")
        self.short8 = short8
        self.long8 = long8

    def run(self, oled):
        self.passing = True
        self.has_run = True

        #sudo wishbone-tool --load-name $SHORT8 --load-address 0x6000000 --load-flash        
        if False == self.run_nonblocking(oled,
               ['sudo', 'wishbone-tool', '--load-name', self.short8, '--load-address', '0x6000000', '--load-flash'],
               reason="Short sample burn failure", timeout=60, title='Short WAV burn:'):
            return self.passing

        if False == self.run_nonblocking(oled,
               ['sudo', 'wishbone-tool', '--load-name', self.long8, '--load-address', '0x6340000', '--load-flash'],
               reason="Long sample burn failure", timeout=120, title='Long WAV burn:'):
            return self.passing

        time.sleep(0.5)
        GPIO.setup(GPIO_PROG_B, GPIO.OUT)
        GPIO.output(GPIO_PROG_B, 0)
        GPIO.setup(GPIO_CRESET_N, GPIO.OUT)
        GPIO.output(GPIO_CRESET_N, 0)
        with canvas(oled) as draw:
            draw.text((0, 0), "Resetting SoC and EC...", fill="white")
        time.sleep(1)
        GPIO.output(GPIO_PROG_B, 1)
        GPIO.setup(GPIO_PROG_B, GPIO.IN)
        GPIO.output(GPIO_CRESET_N, 1)
        GPIO.setup(GPIO_CRESET_N, GPIO.IN)
        
        with canvas(oled) as draw:
            draw.text((0, 0), "SoC firmware burning complete!", fill="white")
        time.sleep(1)
        with canvas(oled) as draw:
            oled.clear()

        if self.logfile:
            self.logfile.write(self.sha256sum(self.short8))
            self.logfile.write(self.sha256sum(self.long8))
        
        return self.passing
    
