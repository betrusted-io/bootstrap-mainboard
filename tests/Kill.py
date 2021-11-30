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

class Test(BaseTest):
    def __init__(self):
        BaseTest.__init__(self, name="Self Destruct", shortname="Kill")

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
            draw.text((0, 0), "Key kill test...", fill="white")
            
        # ensure the correct config: powering off of battery, high current sense mode
        GPIO.output(GPIO_ISENSE, 1)
        time.sleep(0.25)
        GPIO.output(GPIO_BSIM, 1)
        time.sleep(0.5)
        GPIO.output(GPIO_VBUS, 1)
        
        time.sleep(6.0)

        ibus_nom = read_i_vbus()
        #print("pre-kill: {} {}".format(ibat_nom, read_i_vbus()))
        
        # switch to battery power
        GPIO.output(GPIO_VBUS, 0)
        time.sleep(0.5)
        
        self.console = fdspawn(ser)
        self.try_cmd("test kill\r", "|TSTR|KILL")
        self.console.close()

        with canvas(oled) as draw:
            draw.text((0, 1), "A red light should be turned on.", fill="white")
            
        time.sleep(2.0)
        destruct_current = read_i_bat(high_range=True)
        if destruct_current > 0.095:
            self.passing = False
            self.add_reason("SD shutdown current too high {:.4f}A".format(destruct_current))
            if self.logfile:
                self.logfile.write("Self destruct shutdown current: {:.4f}mA\n".format(destruct_current * 1000))

        # print("post-kill: {} {}".format(read_i_bat(high_range=True), read_i_vbus()))
        
        GPIO.output(GPIO_VBUS, 1)
        time.sleep(2.0)
        ibus_kill = read_i_vbus()

        if ibus_kill > (ibus_nom - 0.065):
            self.passing = False
            self.add_reason("Self Destruct fail Q22F/Q21F")
        if self.logfile:
            self.logfile.write("Self destruct vbus current: {:.4f}mA / baseline: {:.4f}\n".format(ibus_kill * 1000, ibus_nom * 1000))
            
        # print("post-vbus: {} {}".format(read_i_bat(high_range=True), read_i_vbus()))
        
        with canvas(oled) as draw:
            draw.text((0, 1), "Key kill test complete", fill="white")

        # disconnect everything so the system can boot again
        GPIO.output(GPIO_VBUS, 0)
        time.sleep(0.5)
        GPIO.output(GPIO_BSIM, 0)
        GPIO.output(GPIO_ISENSE, 1)
        time.sleep(2.0)

        self.has_run = True
        return self.passing
        
