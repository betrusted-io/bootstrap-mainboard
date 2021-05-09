import time
from luma.core.render import canvas
import RPi.GPIO as GPIO
from luma.core.interface.serial import bitbang
from luma.oled.device import ssd1322

from tests.BaseTest import BaseTest
from gpiodefs import *
import sys
import subprocess

class Test(BaseTest):
    def __init__(self, short8="precursors/short_8khz.wav",
                 long8="precursors/long_8khz.wav"):
        BaseTest.__init__(self, name="Audio Clips", shortname="AudWAV")
        self.short8 = short8
        self.long8 = long8

    def reset_board(self, oled):
        GPIO.setup(GPIO_PROG_B, GPIO.OUT)
        GPIO.output(GPIO_PROG_B, 0)
        GPIO.setup(GPIO_CRESET_N, GPIO.OUT)
        GPIO.output(GPIO_CRESET_N, 0)
        time.sleep(0.5)
        with canvas(oled) as draw:
            draw.text((0, 0), "Resetting SoC and EC...", fill="white")
        GPIO.output(GPIO_PROG_B, 1)
        GPIO.setup(GPIO_PROG_B, GPIO.IN)
        GPIO.output(GPIO_CRESET_N, 1)
        GPIO.setup(GPIO_CRESET_N, GPIO.IN)
        time.sleep(1)
        
    def run_wishbone(self, oled, cmdline, reason, showerror=True, timeout=60, title=None):
        with canvas(oled) as draw:
            draw.text((0, 0), "Burning {}".format(title), fill="white")
        start_time = time.time()
        proc = subprocess.Popen(cmdline, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True, bufsize = 0)
        while proc.poll() is None:
            line = proc.stdout.readline()
            with canvas(oled) as draw:
                if title:
                    draw.text((0, 0), title, fill="white")
                draw.text((0, FONT_HEIGHT), line[29:], fill="white") # skip redundant chars
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
        
    def run(self, oled):
        self.passing = True
        self.has_run = True

        #sudo wishbone-tool --load-name $SHORT8 --load-address 0x6000000 --load-flash        
        self.reset_board(oled)

        if False == self.run_wishbone(oled,
               ['sudo', 'wishbone-tool', '--load-name', self.short8, '--load-address', '0x6000000', '--load-flash', "--force-term"],
               reason="Short sample burn failure", timeout=60, title='Short WAV burn:'):
            return self.passing

        self.reset_board(oled)
        
        if False == self.run_wishbone(oled,
               ['sudo', 'wishbone-tool', '--load-name', self.long8, '--load-address', '0x6340000', '--load-flash', "--force-term", "--no-verify"],
               reason="Long sample burn failure", timeout=200, title='Long WAV burn:'):
            return self.passing

        self.reset_board(oled)
        
        with canvas(oled) as draw:
            draw.text((0, 0), "Audio test clip burning complete!", fill="white")
        time.sleep(1)
        with canvas(oled) as draw:
            oled.clear()

        if self.logfile:
            self.logfile.write(self.sha256sum(self.short8))
            self.logfile.write(self.sha256sum(self.long8))
        
        return self.passing
    
