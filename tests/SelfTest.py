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

def slow_send(console, s):
    for c in s:
        console.send(c)
        time.sleep(0.1)

class Test(BaseTest):
    def __init__(self):
        BaseTest.__init__(self, name="Self Test", shortname="SlfTst")

    def run(self, oled):
        self.passing = True
        self.has_run = True

        # make sure the UART is connected
        GPIO.output(GPIO_UART_SOC, 1)
        GPIO.output(GPIO_ISENSE, 1) # set to "high" range, stabilize voltage

        with canvas(oled) as draw:
            draw.text((0, 0), "Power off...", fill="white")
        GPIO.output(GPIO_BSIM, 0)
        GPIO.output(GPIO_VBUS, 0)
        time.sleep(3) # discharge
        
        with canvas(oled) as draw:
            draw.text((0, 0), "Power on...", fill="white")
        GPIO.output(GPIO_VBUS, 1)
        time.sleep(2) # stabilize
        
        with canvas(oled) as draw:
            draw.text((0, 0), "Battery on...", fill="white")
        GPIO.output(GPIO_BSIM, 1)
        
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
        console = fdspawn(ser)        

        with canvas(oled) as draw:
            draw.text((0, 0), "Running self test...", fill="white")

        # wait for boot to finish
        try:
            console.expect_exact("|status: starting main loop", 20)
        except Exception as e:
            self.passing = False
            self.add_reason("OS did not boot in time")
            return self.passing

        time.sleep(3) # give a little time for init scripts to finish running

        slow_send(console, "test factory\r")

        try:
            console.expect_exact("|TSTR|DONE", 10)
        except Exception as e:
            self.passing = False
            self.add_reason("Self test could not run")
            return self.passing

        results = console.before.decode('utf-8')
        for line in results.split('\r'):
            if 'TSTR|' in line:
                self.logfile.write(line.rstrip() + '\n')
                #print(line.rstrip())
                test_output = line.split('|')
                if test_output[2] == 'GYRO':
                    if int(test_output[6]) != 106: # id code
                        self.passing = False
                        self.add_reason("U14W Gyro fail")
                if test_output[2] == 'WF200REV':
                    if int(test_output[3]) != 3 or int(test_output[4]) != 12 or int(test_output[5]) != 3:
                        self.passing = False
                        self.add_reason("U10W WF200 fw rev fail")
                if test_output[2] == 'BATTSTATS':
                    stats = ast.literal_eval(test_output[3])
                    if stats[11] != 44: # id code
                        self.passing = False
                        self.add_reason("U16P BQ25618 fail")
                    if stats[12] < 4000 or stats[12] > 4250: # battery voltage, according to the gas gauge
                        self.passing = False
                        self.add_reason("U11P BQ27421 fail")
                if test_output[2] == 'USBCC':
                    if int(test_output[5]) != 2:
                        self.passing = False
                        self.add_reason("U16P TUSB320 fail")
        
        
        with canvas(oled) as draw:
            draw.text((0, 0), "Self test complete!", fill="white")
        time.sleep(1)
        with canvas(oled) as draw:
            oled.clear()

        console.close()
        return self.passing
    
