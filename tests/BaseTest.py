import time
import subprocess
from luma.core.render import canvas
from luma.core.interface.serial import bitbang
from luma.oled.device import ssd1322
import RPi.GPIO as GPIO
from gpiodefs import *

class BaseTest:
    def __init__(self, name="Unimplemented", shortname=None):
        self.passing = False
        self.has_run = False
        self.name = name
        self.shortlen = 6
        self.reasons = []
        if shortname == None:
            self.shortname = name[:self.shortlen]
        else:
            self.shortname = shortname[:self.shortlen]

    # fail reason
    def fail_reasons(self):
        return self.reasons

    def add_reason(self, reason):
        self.reasons.append(self.__class__.__name__ + ": " + reason)
    
    def short_status(self):
        if self.has_run == False:
            return self.shortname.ljust(self.shortlen) + ' --'
        if self.has_run and self.passing:
            return self.shortname.ljust(self.shortlen) + ' OK'
        else:
            return self.shortname.ljust(self.shortlen) + ' NG'

    def is_passing(self):
        return self.passing

    def has_run(self):
        return self.has_run

    def reset(self):
        self.passing = False
        self.has_run = False
        self.reasons = []

    def wait_start(self):
        while GPIO.input(GPIO_START) == GPIO.LOW:
            time.sleep(0.1)
        while GPIO.input(GPIO_START) == GPIO.HIGH:
            time.sleep(0.1)

    def run_blocking(self, oled, cmdline, reason, showerror=True, timeout=60):
        result = subprocess.run(cmdline, capture_output=True, timeout=timeout)
        if (result.returncode != 0) or (len(result.stderr) != 0):
            if showerror:
                if oled == None: # special case when we're running an EC process that scrambles the OLED pins
                    oled = ssd1322(bitbang(SCLK=11, SDA=10, CE=7, DC=1, RST=12))
                self.display_error(oled, result.stdout, result.stderr)
            self.reasons.append(reason)
            self.passing = False
            return self.passing
            
    def display_error(self, oled, stdout, stderr):
        print("display_error: " + stdout.decode("utf-8") + stderr.decode("utf-8"))
        with canvas(oled) as draw:
            draw.text((0,0), "{} error detail:".format(self.__class__.__name__), fill="white")
            draw.text((0,FONT_HEIGHT*1), "out: " + stdout.decode("utf-8"), fill="white")
            draw.text((0,FONT_HEIGHT*2), "err: " + stderr.decode("utf-8"), fill="white")
            draw.text((0,FONT_HEIGHT*3), "Press START to continue...", fill="white")
        self.wait_start()
        with canvas(oled) as draw:
            oled.clear()
            
    def run(self, oled):
        with canvas(oled) as draw:
            oled.clear()
            draw.text((0,0), "Test '{}' not implemented!".format(self.name))

        time.sleep(1)
        self.has_run = True
        self.passing = False
        self.add_reason("Test not implemented.")

        return self.passing
