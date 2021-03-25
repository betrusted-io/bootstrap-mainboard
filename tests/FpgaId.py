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
    def __init__(self):
        BaseTest.__init__(self, name="FPGA ID", shortname="IDcode")

    def run(self, oled):
        XC7S50_ID = '0x362f093'  # JTAG ID code of the XC7S50
        
        self.passing = True
        self.has_run = True

        with canvas(oled) as draw:
            draw.text((0, 0), "FPGA ID Code Read", fill="white")
        time.sleep(0.5)
        
        # ASSUME: battery power is already on before we run this

        # now capture the ID code data
        result = subprocess.run(['betrusted-scripts/jtag-tools/jtag_gpio.py', '-f', 'betrusted-scripts/jtag-tools/jtag.jtg', '-d', '-r'], capture_output=True, timeout=5)
        
        if (result.returncode != 0):
            self.display_error(oled, result.stdout, result.stderr)
            self.passing = False
            self.reasons.append("FPGA ID code script error")

        # parse and find the metadata
        lines = result.stdout.decode('utf-8').split('\n')
        metadata = {
            "IDCODE" : None,
            "FUSE_DNA" : None,
            "FUSE_USER" : None,
            "FUSE_KEY" : None,
            "FUSE_CNTL" : None,
        }
        token = None
        found_DR = False
        for line in lines:
            for (k,v) in metadata.items():
                if k in line:
                    token = k
                    found_DR = False
            if ('JtagLeg.DR' in line) and (found_DR == False):
                found_DR = True
            if ('result:' in line) and (found_DR == True) and (token != None):
                metadata[token] = line.split(' ')[1]
                token = None
                found_DR = False

        if self.logfile:
            for (k,v) in metadata.items():
                self.logfile.write("{}:{} ".format(k,v))
            self.logfile.write("\n")
            self.logfile.flush()

        if metadata["IDCODE"] != XC7S50_ID:
            self.passing = False
            self.reasons.append("FPGA ID code: got {} / want {}".format(metadata["IDCODE"], XC7S50_ID))
            
        return self.passing
