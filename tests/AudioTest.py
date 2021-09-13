import time
from luma.core.render import canvas
import RPi.GPIO as GPIO
from luma.core.interface.serial import bitbang
from luma.oled.device import ssd1322

from tests.BaseTest import BaseTest
from gpiodefs import *
import sys

import pexpect
from pexpect.fdpexpect import fdspawn
import serial
import ast

class Test(BaseTest):
    def __init__(self):
        BaseTest.__init__(self, name="Audio Test", shortname="Audio")

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
        self.has_run = True

        with canvas(oled) as draw:
            draw.text((0, 0), "Audio / Battery on...", fill="white")
        GPIO.output(GPIO_BSIM, 1)
        time.sleep(0.5)
        
        with canvas(oled) as draw:
            draw.text((0, 0), "Audio / Power on...", fill="white")
        GPIO.output(GPIO_VBUS, 1)

        time.sleep(5) # give a little time for the device to boot

        # open a serial terminal
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
        self.console = fdspawn(ser)        

        # setup for left feed
        GPIO.output(GPIO_AUD_HPR, 0)
        GPIO.output(GPIO_AUD_HPL, 1)
        GPIO.output(GPIO_AUD_SPK, 0)
        
        with canvas(oled) as draw:
            draw.text((0, 0), "Test left audio channel...", fill="white")
        self.try_cmd("test astart 261.63 left\r", "|TSTR|ASTART")
        time.sleep(3)
        self.try_cmd("test astop\r", "|TSTR|ASTOP")

        results = self.console.before.decode('utf-8', errors='ignore')
        for line in results.split('\r'):
            if 'TSTR|' in line:
                if self.logfile:
                    self.logfile.write(line.rstrip() + '\n')
                #print(line.rstrip())
                test_output = line.split('|')
                if test_output[2] == 'ARESULT':
                    if test_output[3] == 'FAIL':
                        self.passing = False
                        self.add_reason("Left audio fail")
        

        # setup for right feed
        GPIO.output(GPIO_AUD_HPR, 1)
        GPIO.output(GPIO_AUD_HPL, 0)
        GPIO.output(GPIO_AUD_SPK, 0)
        
        with canvas(oled) as draw:
            draw.text((0, 0), "Test right audio channel...", fill="white")
        self.try_cmd("test astart 329.63 right\r", "|TSTR|ASTART")
        time.sleep(3)
        self.try_cmd("test astop\r", "|TSTR|ASTOP")

        results = self.console.before.decode('utf-8', errors='ignore')
        for line in results.split('\r'):
            if 'TSTR|' in line:
                if self.logfile:
                    self.logfile.write(line.rstrip() + '\n')
                #print(line.rstrip())
                test_output = line.split('|')
                if test_output[2] == 'ARESULT':
                    if test_output[3] == 'FAIL':
                        self.passing = False
                        self.add_reason("Right audio fail")
        
                        
        # setup for speaker feed
        GPIO.output(GPIO_AUD_HPR, 0)
        GPIO.output(GPIO_AUD_HPL, 0)
        GPIO.output(GPIO_AUD_SPK, 1)
        
        with canvas(oled) as draw:
            draw.text((0, 0), "Test speaker...", fill="white")
        self.try_cmd("test astart 440 speaker\r", "|TSTR|ASTART")
        time.sleep(3)
        self.try_cmd("test astop\r", "|TSTR|ASTOP")

        results = self.console.before.decode('utf-8', errors='ignore')
        for line in results.split('\r'):
            if 'TSTR|' in line:
                if self.logfile:
                    self.logfile.write(line.rstrip() + '\n')
                #print(line.rstrip())
                test_output = line.split('|')
                if test_output[2] == 'ARESULT':
                    if test_output[3] == 'FAIL':
                        self.passing = False
                        self.add_reason("Speaker fail")

        # setup for right/left crosstalk
        GPIO.output(GPIO_AUD_HPR, 0)
        GPIO.output(GPIO_AUD_HPL, 1)
        GPIO.output(GPIO_AUD_SPK, 0)
        
        with canvas(oled) as draw:
            draw.text((0, 0), "Test crosstalk...", fill="white")
        self.try_cmd("test astart 523.25 right\r", "|TSTR|ASTART")
        time.sleep(3)
        self.try_cmd("test astop\r", "|TSTR|ASTOP")

        results = self.console.before.decode('utf-8', errors='ignore')
        for line in results.split('\r'):
            if 'TSTR|' in line:
                if self.logfile:
                    self.logfile.write(line.rstrip() + '\n')
                #print(line.rstrip())
                test_output = line.split('|')
                if test_output[2] == 'ARESULT':
                    if test_output[3] == 'PASS': # we expect this test to FAIL; should be silence in this config
                        self.passing = False
                        self.add_reason("L/R isolation fail")
                        

        # isolate all
        GPIO.output(GPIO_AUD_HPR, 0)
        GPIO.output(GPIO_AUD_HPL, 0)
        GPIO.output(GPIO_AUD_SPK, 0)
                        
        with canvas(oled) as draw:
            draw.text((0, 0), "Audio test complete!", fill="white")
        time.sleep(1)
        with canvas(oled) as draw:
            oled.clear()

        self.console.close()
        return self.passing
    
