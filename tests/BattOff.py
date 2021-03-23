import time
from luma.core.render import canvas
import RPi.GPIO as GPIO

from tests.BaseTest import BaseTest
from gpiodefs import *
from adc128 import *

class Test(BaseTest):
    def __init__(self, ibat_limit = 10):
        BaseTest.__init__(self, name="Batt Off", shortname="BatOff")
        self.ibat_limit = ibat_limit


    def run(self, oled):
        self.passing = True
        
        with canvas(oled) as draw:
            draw.text((0, 0), "Battery simulator off...", fill="white")
            
        # turn on the battery
        GPIO.output(GPIO_BSIM, 0)
        time.sleep(0.5)

        ibat = read_i_bat(high_range=True)

        if ibat > self.ibat_limit:
            self.passing = False
            self.add_reason("IBAT off too high: {:.3f}mA".format(ibat_max))
            GPIO.output(GPIO_BSIM, 0)
        
        self.has_run = True
        return self.passing
        
