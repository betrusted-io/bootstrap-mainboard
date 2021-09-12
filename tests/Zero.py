import time
from luma.core.render import canvas
import RPi.GPIO as GPIO

from tests.BaseTest import BaseTest
from gpiodefs import *
from adc128 import *
from datetime import datetime

class Test(BaseTest):
    def __init__(self):
        BaseTest.__init__(self, name="Zero", shortname="Zero")
        self.ibat_lo_trim = 0.0
        self.ibat_hi_trim = 0.0
        self.ibus_trim = 0.0

    def run(self, oled):
        self.passing = True
        
        GPIO.output(GPIO_ISENSE, 0)
        GPIO.output(GPIO_BSIM, 1)
        GPIO.output(GPIO_VBUS, 1)
        
        with canvas(oled) as draw:
            draw.text((0, 0), "Calibrating...", fill="white")
         
        time.sleep(0.5)

        self.ibat_lo_trim = read_i_bat(high_range=False)
        self.ibus_trim = read_i_vbus()
        self.ibat_hi_trim = read_i_bat(high_range=True)
        
        with canvas(oled) as draw:
            line = 0
            draw.text((0, FONT_HEIGHT * line), "IBUS trim: {:.3f}mA".format(self.ibus_trim * 1000))
            line += 1
            draw.text((0, FONT_HEIGHT * line), "IBAT lo trim: {:.3f}mA".format(self.ibat_lo_trim * 1000))
            line += 1
            draw.text((0, FONT_HEIGHT * line), "IBAT hi trim: {:.3f}mA".format(self.ibat_hi_trim * 1000))
            
        if self.logfile:
            self.logfile.write("IBUS trim    : {:.3f}mA\n".format(self.ibus_trim * 1000))
            self.logfile.write("IBAT low trim: {:.3f}mA\n".format(self.ibat_lo_trim * 1000))
            self.logfile.write("IBAT hi trim : {:.3f}mA\n".format(self.ibat_hi_trim * 1000))

        time.sleep(1.0)

        if self.ibus_trim > 20 or self.ibat_lo_trim > 0.000100 or self.ibat_hi_trim > 0.020:
            self.passing = False
            self.add_reason("Test jig failed to calibrate")

        self.has_run = True
        return self.passing
        
