import time
import io
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
        self.start = time.time()
        if shortname == None:
            self.shortname = name[:self.shortlen]
        else:
            self.shortname = shortname[:self.shortlen]

    def set_env(self, env):
        self.environment = env
        
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

    def reset(self, logfile=None):
        self.passing = False
        self.has_run = False
        self.reasons = []
        self.start = time.time()
        self.logfile = logfile

    def wait_start(self):
        while GPIO.input(GPIO_START) == GPIO.LOW:
            time.sleep(0.1)
        while GPIO.input(GPIO_START) == GPIO.HIGH:
            time.sleep(0.1)

    def sha256sum(self, filename):
        result = subprocess.run(['sha256sum', filename], capture_output=True, env=self.environment)
        if result.returncode != 0:
            return None
        else:
            return result.stdout.decode("utf-8")

    # was meant to be generic but weirdnesses in the jtag_gpio.py script has made this more specific than we'd like
    def run_nonblocking(self, oled, cmdline, reason, showerror=True, timeout=60, title=None):
        start_time = time.time()
        proc = subprocess.Popen(cmdline, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, bufsize = 0, env=self.environment)
        while proc.poll() is None:
            line = proc.stderr.readline()
            with canvas(oled) as draw:
                if title:
                    draw.text((0, 0), title, fill="white")
                draw.text((0, FONT_HEIGHT), line, fill="white")
            if time.time() - start_time > timeout:
                self.passing = False
                proc.kill()
                self.reasons.append("[Timeout] " + reason)
                if showerror:
                   with canvas(oled) as draw:
                      draw.text((0, FONT_HEIGHT*0), reason, fill="white")
                      draw.text((0, FONT_HEIGHT*1), "Operation timeout!", fill="white")
                      self.wait_start()
                return self.passing
        if proc.poll() != 0:
            if showerror:
               with canvas(oled) as draw:
                  draw.text((0, FONT_HEIGHT*0), reason, fill="white")
                  draw.text((0, FONT_HEIGHT*1), "Did not complete!", fill="white")
                  self.wait_start()
            self.passing = False
            proc.kill()
            self.reasons.append(reason)
            return self.passing
        return self.passing

    # used primarily for EC programming, because you can't mux oled + EC as they share the SPI pins
    def run_blocking(self, oled, cmdline, reason, showerror=True, timeout=60):
        result = subprocess.run(cmdline, capture_output=True, timeout=timeout, env=self.environment)
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
        if self.logfile:
            self.logfile.write("display_error detail: \n")
            self.logfile.write(stdout.decode("utf-8"))
            self.logfile.write(stderr.decode("utf-8"))
            
    def run(self, oled):
        with canvas(oled) as draw:
            oled.clear()
            draw.text((0,0), "Test '{}' not implemented!".format(self.name))

        time.sleep(1)
        self.has_run = True
        self.passing = False
        self.add_reason("Test not implemented.")

        return self.passing
