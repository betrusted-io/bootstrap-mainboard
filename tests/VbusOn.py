import time
from luma.core.render import canvas
import RPi.GPIO as GPIO

from tests.BaseTest import BaseTest
from gpiodefs import *
from adc128 import *

class Test(BaseTest):
    def __init__(self, vbus_min_limit=4.5, vbus_max_limit=5.5):
        BaseTest.__init__(self, name="Vbus On", shortname="VbusOn")
        self.vbus_min_limit = vbus_min_limit
        self.vbus_max_limit = vbus_max_limit

    def run(self, oled):
        self.passing = True
        
        with canvas(oled) as draw:
            draw.text((0, 0), "VBUS on...", fill="white")
            
        # turn on the power
        GPIO.output(GPIO_VBUS, 1)
        time.sleep(0.5) # wait for power to stabilize

        vbus = read_vbus()

        if vbus < self.vbus_min_limit:
            self.passing = False
            self.add_reason("VBUS too low: {:.3f}V".format(vbus_min))
            GPIO.output(GPIO_VBUS, 0)
        if vbus > self.vbus_max_limit:
            self.passing = False
            self.add_reason("VBUS too high: {:3.f}V".format(vbus_max))
            GPIO.output(GPIO_VBUS, 0)
        
        self.has_run = True
        return self.passing
        
