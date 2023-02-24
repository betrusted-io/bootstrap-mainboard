import time
from luma.core.render import canvas
import RPi.GPIO as GPIO
from luma.core.interface.serial import bitbang
from luma.oled.device import ssd1322

from tests.BaseTest import BaseTest
from gpiodefs import *
import sys

class Test(BaseTest):
    def __init__(self, fpga="precursors/soc_csr.bin"):
        BaseTest.__init__(self, name="SoC Firmware", shortname="FPGApr")
        self.fpga = fpga

    def run(self, oled):
        self.passing = True
        self.has_run = True

        with canvas(oled) as draw:
            draw.text((0, 0), "Soc fw/Power off...", fill="white")
        GPIO.output(GPIO_BSIM, 0)
        GPIO.output(GPIO_VBUS, 0)
        time.sleep(3) # discharge
        
        with canvas(oled) as draw:
            draw.text((0, 0), "Soc fw/Power on...", fill="white")
        GPIO.output(GPIO_VBUS, 1)
        time.sleep(2) # stabilize
        
        with canvas(oled) as draw:
            draw.text((0, 0), "Soc fw/Battery on...", fill="white")
        GPIO.output(GPIO_BSIM, 1)
        
        if False == self.run_nonblocking(oled,
               ['betrusted-scripts/jtag-tools/jtag_gpio.py', '-f', self.fpga, '--raw-binary', '--spi-mode', '-r'],
               reason="FPGA bitstream burn failure", timeout=80, title='FPGA bitstream:'):
            return self.passing

        
        time.sleep(0.5)
        GPIO.setup(GPIO_PROG_B, GPIO.OUT)
        GPIO.output(GPIO_PROG_B, 0)
        GPIO.setup(GPIO_CRESET_N, GPIO.OUT)
        GPIO.output(GPIO_CRESET_N, 0)
        with canvas(oled) as draw:
            draw.text((0, 0), "Resetting SoC and EC...", fill="white")
        time.sleep(1)
        GPIO.output(GPIO_PROG_B, 1)
        GPIO.setup(GPIO_PROG_B, GPIO.IN)
        GPIO.output(GPIO_CRESET_N, 1)
        GPIO.setup(GPIO_CRESET_N, GPIO.IN)
        
        with canvas(oled) as draw:
            draw.text((0, 0), "SoC firmware burning complete!", fill="white")
        time.sleep(1)
        with canvas(oled) as draw:
            oled.clear()

        if self.logfile:
            self.logfile.write(self.sha256sum(self.fpga))
        
        return self.passing
    
