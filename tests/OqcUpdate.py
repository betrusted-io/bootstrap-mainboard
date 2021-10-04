import time
from luma.core.render import canvas
import RPi.GPIO as GPIO
from luma.core.interface.serial import bitbang
from luma.oled.device import ssd1322

from tests.BaseTest import BaseTest
from gpiodefs import *
import sys

import subprocess
import urllib.request
import time

def get_url(url):
     max_attempts = 10
     attempts = 0
     sleeptime = 5 #in seconds, no reason to continuously try if network is down

     while attempts < max_attempts:
         with urllib.request.urlopen(url, timeout = 30) as response:
             content = response.read()
             return content
         attempts += 1
         time.sleep(sleeptime)
     return None

class Test(BaseTest):
    def __init__(self):
        BaseTest.__init__(self, name="OQC Update only", shortname="OQCup")

    def run_usb(self, oled, cmdline, reason, showerror=True, timeout=60, title=None):
        passing = True
        with canvas(oled) as draw:
            draw.text((0, 0), "Burning {}".format(title), fill="white")
        start_time = time.time()
        last_draw = time.time()
        proc = subprocess.Popen(cmdline, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True, bufsize = 0, env=self.environment, shell=False)
        while proc.poll() is None:
            line = proc.stdout.readline()
            # print(line)
            if self.logfile and "Elapsed" not in line:
                self.logfile.write(line)
                self.logfile.flush()
            if time.time() - last_draw > 0.5: # rate limit drawing to reduce CPU load...
                with canvas(oled) as draw:
                    if title:
                        draw.text((0, 0), title, fill="white")
                    draw.text((0, FONT_HEIGHT), line, fill="white")
                last_draw = time.time()
            if time.time() - start_time > timeout:
                passing = False
                proc.kill()
                self.reasons.append("[Timeout] " + reason)
                if showerror:
                   with canvas(oled) as draw:
                      draw.text((0, FONT_HEIGHT*0), reason, fill="white")
                      draw.text((0, FONT_HEIGHT*1), "Operation timeout!", fill="white")
                      draw.text((0, FONT_HEIGHT*4), "Press start to continue...", fill="white")
                   self.wait_start()
                return passing
        # print("run done")
        if proc.poll() != 0:
            print("run resulted in error")
            if showerror:
               with canvas(oled) as draw:
                  draw.text((0, FONT_HEIGHT*0), reason, fill="white")
                  draw.text((0, FONT_HEIGHT*1), "Did not complete!", fill="white")
                  draw.text((0, FONT_HEIGHT*4), "Press start to continue...", fill="white")
               self.wait_start()
            passing = False
            proc.kill()
            self.reasons.append(reason)
            return passing
        return passing
        
    def run(self, oled):
        self.passing = True
        self.has_run = True

        GPIO.output(GPIO_VBUS, 1) # turn on the VBUS

        with canvas(oled) as draw:
            draw.text((0, 0), "Fetch revision...", fill="white")
        rev = get_url("https://ci.betrusted.io/releases/LATEST")
        revpath = "releases/" + rev.decode("utf-8").strip()

        update_dict = {
            'loader.bin' : '-l',
            'xous.img' : '-k',
            'soc_csr.bin' : '--soc',
            'ec_fw.bin' : '-e',
            'wf200_fw.bin' : '-w',
        }
        for name, switch in update_dict.items():
            url = "https://ci.betrusted.io/{}/{}".format(revpath, name)
            object = get_url(url)
            with canvas(oled) as draw:
                draw.text((0, 0), "Fetch {}".format(url), fill="white")
            if object == None:
                 with canvas(oled) as draw:
                     draw.text((0, 0), "Network error! Check cable.", fill="white")
                     draw.text((1, FONT_HEIGHT * 1), url, fill="white")
                     time.sleep(2)
                 return False
            with open("/tmp/staging", "wb") as f:
                f.write(object)
                f.close()
            if False == self.run_usb(oled,
                   ['/home/pi/code/bootstrap-mainboard/betrusted-scripts/usb_update.py', '--force', switch, "/tmp/staging"],
                   reason="USB update failure of {}".format(name), timeout=500, title='Updating {}'.format(name)):
                return False
            if self.logfile:
                self.logfile.write("OQC update of {} ".format(name))
                self.logfile.write(self.sha256sum("/tmp/staging"))
                self.logfile.flush()
            time.sleep(1)
        
        return self.passing
    
