import time
from luma.core.render import canvas
import RPi.GPIO as GPIO

from tests.BaseTest import BaseTest
from gpiodefs import *
from adc128 import *

class Test(BaseTest):
    def __init__(self):
        BaseTest.__init__(self, name="Power On", shortname="PwrOn")

    def run(self, oled):
        self.passing = True
        
        # turn on the power
        GPIO.output(GPIO_VBUS, 1)
        GPIO.output(GPIO_BSIM, 1)
        time.sleep(0.5) # wait for power to stabilize

        oled.clear()
        line = 0
        vbus_max = 0.0
        vbus_min = 10.0
        ibat_max = 0.0
        ibus_max = 0.0
        for x in range(20, 0, -1):
            if x == 20 or x == 10 or x == 1:
                with canvas(oled) as draw:
                    draw.text((0, FONT_HEIGHT * line), "Measuring current... {}".format(int(x/10)), fill="white")
            time.sleep(0.1)
            # sample
            vbus = read_vbus()
            ibat = read_i_bat(high_range=True)
            ibus = read_i_vbus()
            if vbus > vbus_max:
                vbus_max = vbus
            if vbus < vbus_min:
                vbus_min = vbus
            if ibat > ibat_max:
                ibat_max = ibat
            if ibus > ibus_max:
                ibus_max = ibus

        # turn off the power
        GPIO.output(GPIO_VBUS, 0)
        GPIO.output(GPIO_BSIM, 0)

        # this criteria has not been tuned
        ###############################
        if ibat_max > 250:
            self.passing = False
            self.add_reason("IBAT too high: {:.3f}mA".format(ibat_max))
        if ibus_max > 800:
            self.passing = False
            self.add_reason("IBUS too high: {:.3f}mA".format(ibus_max))
        if vbus_min < 4.5:
            self.passing = False
            self.add_reason("VBUS too low: {:.3f}V".format(vbus_min))
        if vbus_max > 5.5:
            self.passing = False
            self.add_reason("VBUS too high: {:3.f}V".format(vbus_max))
        ###############################
        
        with canvas(oled) as draw:
            line = 0
            draw.text((0, FONT_HEIGHT * line), "VBUS: {:.3f}V".format(vbus))
            line += 1
            draw.text((0, FONT_HEIGHT * line), "IBUS: {:.3f}mA".format(ibus * 1000))
            line += 1
            draw.text((0, FONT_HEIGHT * line), "IBAT: {:.3f}mA".format(ibat * 1000))
            #line += 1
            #draw.text((0, FONT_HEIGHT * line), "Press START to continue")

        #while GPIO.input(GPIO_START) == GPIO.LOW:
        #    time.sleep(0.1)
        time.sleep(1.0)

        self.has_run = True
        return self.passing
        
