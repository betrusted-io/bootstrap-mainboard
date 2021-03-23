import time
from luma.core.render import canvas
import RPi.GPIO as GPIO

from tests.BaseTest import BaseTest
from gpiodefs import *
from adc128 import *

class Test(BaseTest):
    def __init__(self, vbus_min_limit=0, vbus_max_limit=0.8):
        BaseTest.__init__(self, name="Vbus On", shortname="VbsOff")
        self.vbus_min_limit = vbus_min_limit
        self.vbus_max_limit = vbus_max_limit

    def run(self, oled):
        self.passing = True
        
        with canvas(oled) as draw:
            draw.text((0, 0), "VBUS off...", fill="white")
            
        # turn on the power
        GPIO.output(GPIO_VBUS, 0)
        time.sleep(1.5) # wait to discharge

        vbus = read_vbus()

        if vbus < self.vbus_min_limit:
            self.passing = False
            self.add_reason("VBUS off too low: {:.3f}V".format(vbus_min))
        if vbus > self.vbus_max_limit:
            self.passing = False
            self.add_reason("VBUS off too high: {:3.f}V".format(vbus_max))
        
        self.has_run = True
        return self.passing
        
