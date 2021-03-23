import time
from luma.core.render import canvas
import RPi.GPIO as GPIO

from tests.base import Test
from gpiodefs import *
from adc128 import *

class PowerOn(Test):
    def __init__(self):
        Test.__init__(self, name="Power On", shortname="PwrOn")

    def run(self, oled):
        # turn on the power
        GPIO.output(GPIO_VBUS, 1)
        GPIO.output(GPIO_BSIM, 1)
        time.sleep(0.5) # wait for power to stabilize

        oled.clear()
        line = 0
        for x in range(5, 0, -1):
            with canvas(oled) as draw:
                draw.text((0, FONT_HEIGHT * line), "Measuring current... {}".format(x), fill="white")
                time.sleep(1.0)

        with canvas(oled) as draw:
            vbus = read_vbus()
            ibat = read_i_bat(high_range=True)
            ibus = read_i_vbus()
            line = 0
            draw.text((0, FONT_HEIGHT * line), "VBUS: {:.3f}V".format(vbus))
            line += 1
            draw.text((0, FONT_HEIGHT * line), "IBUS: {:.3f}mA".format(ibus * 1000))
            line += 1
            draw.text((0, FONT_HEIGHT * line), "IBAT: {:.3f}mA".format(ibat * 1000))
            line += 1
            draw.text((0, FONT_HEIGHT * line), "Press START to continue")

        # turn off the power
        GPIO.output(GPIO_VBUS, 0)
        GPIO.output(GPIO_BSIM, 0)
        while GPIO.input(GPIO_START) == GPIO.LOW:
            time.sleep(0.1)

        self.has_run = True
        self.passing = True
        return self.passing
        
