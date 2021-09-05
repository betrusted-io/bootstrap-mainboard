import time
from luma.core.render import canvas
import RPi.GPIO as GPIO
from luma.core.interface.serial import bitbang
from luma.oled.device import ssd1322

from tests.BaseTest import BaseTest
from gpiodefs import *
import sys

class Test(BaseTest):
    def __init__(self, fpga="precursors/soc_csr.bin",
                 loader="precursors/loader.bin", kernel="precursors/xous.img"):
        BaseTest.__init__(self, name="SoC Firmware", shortname="FPGApr")
        self.fpga = fpga
        self.loader = loader
        self.kernel = kernel

    def run(self, oled):
        self.passing = True
        self.has_run = True

        
        if False == self.run_nonblocking(oled,
               ['betrusted-scripts/jtag-tools/jtag_gpio.py', '-f', self.fpga, '--raw-binary', '--spi-mode', '-r'],
               reason="FPGA bitstream burn failure", timeout=60, title='FPGA bitstream:'):
            return self.passing

        
        if False == self.run_nonblocking(oled,
               ['betrusted-scripts/jtag-tools/jtag_gpio.py', '-f', self.loader, '--raw-binary', '-a', '0x500000', '-s', '-r'],
               reason="Loader burn failure", timeout=60, title='Loader:'):
            return self.passing

        
        if False == self.run_nonblocking(oled,
               ['betrusted-scripts/jtag-tools/jtag_gpio.py', '-f', self.kernel, '--raw-binary', '-a', '0x980000', '-s', '-r', '-n'],
               reason="Kernel burn failure", timeout=60, title='Kernel:'):
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
            self.logfile.write(self.sha256sum(self.loader))
            self.logfile.write(self.sha256sum(self.kernel))
        
        return self.passing
    
