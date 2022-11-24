import time
from luma.core.render import canvas
import RPi.GPIO as GPIO

from tests.BaseTest import BaseTest
from gpiodefs import *
from adc128 import *
from datetime import datetime

import pexpect
from pexpect.fdpexpect import fdspawn
import serial
import subprocess

class Test(BaseTest):
    def __init__(self):
        BaseTest.__init__(self, name="Power Off", shortname="PwrOff")

    def slow_send(self, s):
        for c in s:
            self.console.send(c)
            time.sleep(0.1)

    def try_cmd(self, cmd, expect, timeout=20):
        self.slow_send(cmd)
        try:
            self.console.expect_exact(expect, timeout)
        except Exception as e:
            self.passing = False
            self.add_reason(cmd.strip())
        
    def run_usb(self, oled, cmdline, reason, showerror=True, timeout=60, title=None):
        passing = True
        with canvas(oled) as draw:
            draw.text((0, 0), "Burning {}".format(title), fill="white")
        start_time = time.time()
        proc = subprocess.Popen(cmdline, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True, bufsize = 0, env=self.environment, shell=False)
        while proc.poll() is None:
            line = proc.stdout.readline()
            #print(line)
            if self.logfile and "Elapsed" not in line:
                self.logfile.write(line)
            with canvas(oled) as draw:
                if title:
                    draw.text((0, 0), title, fill="white")
                draw.text((0, FONT_HEIGHT), line[29:], fill="white") # skip redundant chars
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
        if proc.poll() != 0:
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

        # open a serial terminal, make sure WFI is off so we have a consistent power measurement
        ser = serial.Serial()
        ser.baudrate = 115200
        ser.port="/dev/ttyS0"
        ser.stopbits=serial.STOPBITS_ONE
        ser.xonxoff=0
        try:
            ser.open()
        except:
            print("couldn't open serial port")
            exit(1)
        
        with canvas(oled) as draw:
            draw.text((0, 0), "Post-test current...", fill="white")
            
        # ensure the correct config: powering off of battery, high current sense mode
        GPIO.output(GPIO_ISENSE, 1)
        time.sleep(0.25)
        GPIO.output(GPIO_BSIM, 1)
        time.sleep(0.5)
        GPIO.output(GPIO_VBUS, 1)
        time.sleep(0.5)
        GPIO.output(GPIO_VBUS, 0)
        
        time.sleep(10.0) # total time required from boot to command acceptance
        self.console = fdspawn(ser)        
        self.try_cmd("test wfioff\r", "|TSTR|WFIOFF")
        self.console.close()
        
        vbus = read_vbus()

        # demonstrate that vbus is at 0
        if vbus > 1.0:
            self.passing = False
            self.add_reason("VBUS did not drop: {:.3f}V".format(vbus))

        oled.clear()
        line = 0
        ibat_max = 0.290
        ibat_min = 0.180

        ibat_avg = 0.0
        time.sleep(12)
        for x in range(10, 0, -1):
            if x == 10 or x == 5 or x == 1:
                with canvas(oled) as draw:
                    draw.text((0, FONT_HEIGHT * line), "Measuring current... {}".format(int(x/5)), fill="white")
            time.sleep(0.2)
            # sample
            ibat_avg += read_i_bat(high_range=True)

        ibat_avg /= 10.0

        if ibat_avg > ibat_max:
            self.passing = False
            self.add_reason("IBAT too high: {:.3f}mA".format(ibat_avg * 1000))
        if ibat_avg < ibat_min:
            self.passing = False
            self.add_reason("IBAT too low: {:.3f}mA".format(ibat_avg * 1000))
        
        with canvas(oled) as draw:
            line = 0
            draw.text((0, FONT_HEIGHT * line), "Post-test current measurement:")
            line += 1
            draw.text((0, FONT_HEIGHT * line), "VBUS: {:.3f}V".format(vbus))
            line += 1
            draw.text((0, FONT_HEIGHT * line), "IBAT: {:.3f}mA".format(ibat_avg * 1000))
            
        if self.logfile:
            self.logfile.write("Post-test current measured at {}\n".format(str(datetime.now())))
            self.logfile.write("VBUS: {:.3f}V\n".format(vbus))
            self.logfile.write("IBAT: {:.3f}mA\n".format(ibat_avg * 1000))

        # reset the "don't ask again" toggle for root key init.
        # /home/pi/code/bootstrap-mainboard/betrusted-scripts/usb_update.py --image precursors/ff_sector.bin 0x27F000
        time.sleep(1.0)
        if False == self.run_usb(oled,
               ['/home/pi/code/bootstrap-mainboard/betrusted-scripts/usb_update.py', '--image',
                'precursors/ff_sector.bin', '0x27F000'],
                 reason="Reset don't ask reset failure", timeout=90, title="Resetting don't ask flag: "):
            self.logfile.write("Don't ask flag reset failed")
            self.passing = False

        time.sleep(1.0)

        GPIO.output(GPIO_BSIM, 0)
        GPIO.output(GPIO_VBUS, 0) # should already be off, doesn't hurt to check

        self.has_run = True
        return self.passing
        
