import time
from luma.core.render import canvas
import RPi.GPIO as GPIO
from luma.core.interface.serial import bitbang
from luma.oled.device import ssd1322

from tests.BaseTest import BaseTest
from gpiodefs import *
import sys

class Test(BaseTest):
    def __init__(self, wfx_firmware="betrusted-scripts/wfx-firmware/wfm_wf200_C0.sec",
                 ec_firmware="precursors/bt-ec.bin"):
        BaseTest.__init__(self, name="EC Firmware", shortname="EcBurn")
        self.wfx_firmware = wfx_firmware
        self.ec_firmware = ec_firmware

    def run(self, oled):
        self.passing = True
        self.has_run = True

        with canvas(oled) as draw:
            draw.text((0, 0), "Burning WFX firmware...", fill="white")
        time.sleep(0.5)

        # oled is None for EC because the firmware burner program is contra-indicated with the oled interface
        # (as in they share the same pins so the interface has to be rebuilt after every call)
        if False == self.run_blocking(None,
               ['sudo', 'fomu-flash/fomu-flash', '-w', self.wfx_firmware, '-a', '0x9C000', '-q'],
               reason="EC|WFX firmware burn failure", timeout=60):
            return self.passing

        # must regenerate the OLED interface because it's co-opted by the EC firmware commands
        oled.cleanup()
        oled = ssd1322(bitbang(SCLK=11, SDA=10, CE=7, DC=1, RST=12))
        with canvas(oled) as draw:
            draw.text((0, 0), "Verifying WFX firmware...", fill="white")
        time.sleep(0.5)
        
        if False == self.run_blocking(None,
               ['sudo', 'fomu-flash/fomu-flash', '-v', self.wfx_firmware, '-a', '0x9C000', '-q'],
               reason="EC|WFX firmware verify failure", timeout=10):
            return self.passing

        oled.cleanup()
        oled = ssd1322(bitbang(SCLK=11, SDA=10, CE=7, DC=1, RST=12))
        with canvas(oled) as draw:
            draw.text((0, 0), "Burning EC firmware...", fill="white")
        time.sleep(0.5)
        
        if False == self.run_blocking(None,
               ['sudo', 'fomu-flash/fomu-flash', '-4'],
               reason="Set QSPI mode", timeout=2):
            return self.passing
        
        if False == self.run_blocking(None,
               ['sudo', 'fomu-flash/fomu-flash', '-w', self.ec_firmware, '-q'],
               reason="EC main firmware burn failure", timeout=60):
            return self.passing
        
        oled.cleanup()
        oled = ssd1322(bitbang(SCLK=11, SDA=10, CE=7, DC=1, RST=12))
        with canvas(oled) as draw:
            draw.text((0, 0), "Verifying EC firmware...", fill="white")
        time.sleep(0.5)
        
        if False == self.run_blocking(None,
               ['sudo', 'fomu-flash/fomu-flash', '-v', self.ec_firmware, '-q'],
               reason="EC main firmware verify failure", timeout=10):
            return self.passing

        oled.cleanup()
        oled = ssd1322(bitbang(SCLK=11, SDA=10, CE=7, DC=1, RST=12))
        with canvas(oled) as draw:
            draw.text((0, 0), "Restarting EC...", fill="white")
        time.sleep(0.5)
        
        if False == self.run_blocking(None,
               ['sudo', 'fomu-flash/fomu-flash', '-r'],
               reason="EC reboot failure", timeout=10):
            return self.passing

        ### this code is bad because you can't draw to the OLED while flashing
        #process = subprocess.Popen(['sudo', 'fomu-flash/fomu-flash', '-w', self.wfx_firmware, '-a', '0x9C000'], stdout=subprocess.PIPE)
        #for line in iter(process.stdout.readline, b''):
        #    with canvas(oled) as draw:
        #        draw.text((0, 0), line, fill="white")

        oled.cleanup()
        oled = ssd1322(bitbang(SCLK=11, SDA=10, CE=7, DC=1, RST=12))
        with canvas(oled) as draw:
            draw.text((0, 0), "EC burning complete!", fill="white")
        time.sleep(1)
        with canvas(oled) as draw:
            oled.clear()
        
        return self.passing
    
