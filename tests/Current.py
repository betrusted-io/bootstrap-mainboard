import time
from luma.core.render import canvas
import RPi.GPIO as GPIO

from tests.BaseTest import BaseTest
from gpiodefs import *
from adc128 import *
from datetime import datetime

class Test(BaseTest):
    def __init__(self, ibat_limit=250, ibus_limit=580, vbus_min_limit=4.5, vbus_max_limit=5.5):
        BaseTest.__init__(self, name="Power On", shortname="PwrOn")
        self.ibat_limit = ibat_limit
        self.ibus_limit = ibus_limit
        self.vbus_min_limit = vbus_min_limit
        self.vbus_max_limit = vbus_max_limit

    def run(self, oled):
        self.passing = True
        
        # wait for power to stabilize from previous test
        time.sleep(0.5)

        oled.clear()
        line = 0
        vbus_max = 0.0
        vbus_min = 10.0
        ibat_max = 0.0
        ibus_max = 0.0
        for x in range(10, 0, -1):
            if x == 10 or x == 5 or x == 1:
                with canvas(oled) as draw:
                    draw.text((0, FONT_HEIGHT * line), "Measuring current... {}".format(int(x/5)), fill="white")
            time.sleep(0.2)
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

        if ibat_max > self.ibat_limit:
            self.passing = False
            self.add_reason("IBAT too high: {:.3f}mA".format(ibat_max))
        if ibus_max > self.ibus_limit:
            self.passing = False
            self.add_reason("IBUS too high: {:.3f}mA".format(ibus_max))
        if vbus_min < self.vbus_min_limit:
            self.passing = False
            self.add_reason("VBUS too low: {:.3f}V".format(vbus_min))
        if vbus_max > self.vbus_max_limit:
            self.passing = False
            self.add_reason("VBUS too high: {:.3f}V".format(vbus_max))
        
        with canvas(oled) as draw:
            line = 0
            draw.text((0, FONT_HEIGHT * line), "VBUS: {:.3f}V".format(vbus))
            line += 1
            draw.text((0, FONT_HEIGHT * line), "IBUS: {:.3f}mA".format(ibus * 1000))
            line += 1
            draw.text((0, FONT_HEIGHT * line), "IBAT: {:.3f}mA".format(ibat * 1000))
            #line += 1
            #draw.text((0, FONT_HEIGHT * line), "Press START to continue")
            
        if self.logfile:
            self.logfile.write("Current measured at {}\n".format(str(datetime.now())))
            self.logfile.write("VBUS: {:.3f}V\n".format(vbus))
            self.logfile.write("IBUS: {:.3f}mA\n".format(ibus * 1000))
            self.logfile.write("IBAT: {:.3f}mA\n".format(ibat * 1000))

        time.sleep(1.0)

        self.has_run = True
        return self.passing
        
