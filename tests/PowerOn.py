import time
from luma.core.render import canvas
import RPi.GPIO as GPIO

from tests.BaseTest import BaseTest
from gpiodefs import *
from adc128 import *
from datetime import datetime

class Test(BaseTest):
    def __init__(self, vbus_min_limit=4.5, vbus_max_limit=5.5):
        BaseTest.__init__(self, name="Power On", shortname="PwrOn")
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

        # do a quick-fail if there is a short on vbus
        if vbus < self.vbus_min_limit:
            self.passing = False
            self.add_reason("VBUS too low: {:.3f}V".format(vbus_min))
            GPIO.output(GPIO_VBUS, 0)
            return self.passing
        if vbus > self.vbus_max_limit:
            self.passing = False
            self.add_reason("VBUS too high: {:.3f}V".format(vbus_max))
            GPIO.output(GPIO_VBUS, 0)
            return self.passing

        # wait for power to stabilize from previous test
        time.sleep(0.5)

        with canvas(oled) as draw:
            draw.text((0, 0), "Battery simulator on...", fill="white")
            
        # turn on the battery
        GPIO.output(GPIO_BSIM, 1)
        time.sleep(0.5) # wait for power to stabilize

        oled.clear()
        line = 0
        vbus_max = 0.0
        vbus_min = 10.0
        ibat_max = 0.0
        ibus_max = 0.0
        ibus_avg = 0.0
        ibat_avg = 0.0
        for x in range(10, 0, -1):
            if x == 10 or x == 5 or x == 1:
                with canvas(oled) as draw:
                    draw.text((0, FONT_HEIGHT * line), "Measuring current... {}".format(int(x/5)), fill="white")
            time.sleep(0.2)
            # sample
            vbus = read_vbus()
            ibat = read_i_bat(high_range=True)
            ibus = read_i_vbus()
            ibat_avg += ibat
            ibus_avg += ibus
            if vbus > vbus_max:
                vbus_max = vbus
            if vbus < vbus_min:
                vbus_min = vbus
            if ibat > ibat_max:
                ibat_max = ibat
            if ibus > ibus_max:
                ibus_max = ibus
        ibat_avg /= 10.0
        ibus_avg /= 10.0

        ibat_limit = 20 # should be no draw from the battery at initial power-on
        ibus_limit = 650 # we'll be charging the battery plus potentially powering up the SoC
                
        if ibat_max > ibat_limit:
            self.passing = False
            self.add_reason("IBAT too high: {:.3f}mA".format(ibat_max))
        if ibus_max > ibus_limit:
            self.passing = False
            self.add_reason("IBUS too high: {:.3f}mA".format(ibus_max))
        if vbus_min < self.vbus_min_limit:
            self.passing = False
            self.add_reason("VBUS too low: {:.3f}V".format(vbus_min))
        if vbus_max > self.vbus_max_limit:
            self.passing = False
            self.add_reason("VBUS too high: {:.3f}V".format(vbus_max))
        if ibus_max < 0.005:
            self.passing = False
            self.add_reason("IBUS too low: {:.3f}mA".format(ibus_max))
        
        with canvas(oled) as draw:
            line = 0
            draw.text((0, FONT_HEIGHT * line), "VBUS: {:.3f}V".format(vbus))
            line += 1
            draw.text((0, FONT_HEIGHT * line), "IBUS: {:.3f}mA".format(ibus_avg * 1000))
            line += 1
            draw.text((0, FONT_HEIGHT * line), "IBAT: {:.3f}mA".format(ibat_avg * 1000))
            #line += 1
            #draw.text((0, FONT_HEIGHT * line), "Press START to continue")
            
        if self.logfile:
            self.logfile.write("Power-on current measured at {}\n".format(str(datetime.now())))
            self.logfile.write("VBUS: {:.3f}V\n".format(vbus))
            self.logfile.write("IBUS: {:.3f}mA\n".format(ibus_avg * 1000))
            self.logfile.write("IBAT: {:.3f}mA\n".format(ibat_avg * 1000))

        time.sleep(0.5)

        self.has_run = True
        return self.passing
        
