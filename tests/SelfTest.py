import time
from luma.core.render import canvas
import RPi.GPIO as GPIO
from luma.core.interface.serial import bitbang
from luma.oled.device import ssd1322

from tests.BaseTest import BaseTest
from gpiodefs import *
from adc128 import *
import sys

import pexpect
from pexpect.fdpexpect import fdspawn
import serial
import ast

VIBE_HAPPENED=False

def vibe_callback(channel):
     global VIBE_HAPPENED
     VIBE_HAPPENED = True

class Test(BaseTest):
    def __init__(self):
        BaseTest.__init__(self, name="Self Test", shortname="SlfTst")

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
        global VIBE_HAPPENED
        
        self.passing = True
        self.has_run = True

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

        # make sure that the CRESET_N is de-asserted
        # actually this doesn't need to be a tri-state because this goes through an open-collector driver
        GPIO.setup(GPIO_CRESET_N, GPIO.OUT)
        GPIO.output(GPIO_CRESET_N, 1)
        
        # make sure the UART is connected
        GPIO.output(GPIO_UART_SOC, 1)
        GPIO.output(GPIO_ISENSE, 1) # set to "high" range, stabilize voltage

        with canvas(oled) as draw:
            draw.text((0, 0), "Selftest / Power off...", fill="white")
        GPIO.output(GPIO_BSIM, 0)
        GPIO.output(GPIO_VBUS, 0)
        time.sleep(3) # discharge
        
        with canvas(oled) as draw:
            draw.text((0, 0), "Selftest / Battery on...", fill="white")
        GPIO.output(GPIO_BSIM, 1)
        
        with canvas(oled) as draw:
            draw.text((0, 0), "Selftest / Power on...", fill="white")
        GPIO.output(GPIO_VBUS, 1)
        time.sleep(0.5)
        GPIO.output(GPIO_VBUS, 0) # self-test is done on 'battery power' to control i-measurements

        with canvas(oled) as draw:
            draw.text((0, 0), "Running self test...", fill="white")

        # wait for boot to finish
        try:
            self.console.expect_exact("|status: starting main loop", 20)
        except Exception as e:
            self.passing = False
            self.add_reason("OS did not boot in time")
            return self.passing

        time.sleep(5) # give a little time for init scripts to finish running

        #### at this moment, VBUS is off. test boost mode.
        with canvas(oled) as draw:
            draw.text((0, 0), "Selftest / Boost...", fill="white")
        vbus = read_vbus()
        #print("vbus before: {}", vbus)
        if vbus > 1.0:
            self.passing = False
            self.add_reason("VBUS leakage (boost mode Q14P)")
            
        self.try_cmd("test booston\r", "|TSTR|BOOSTON", timeout=10)
        time.sleep(1)
        vbus = read_vbus()

        if vbus < 4.5:
            self.passing = False
            self.add_reason("VBUS boost too low (Q14P/U17P)")
        if self.logfile:
            self.logfile.write("VBoost: {:.3f}V\n".format(vbus))
        
        self.try_cmd("test boostoff\r", "|TSTR|BOOSTOFF", timeout=10) 
        time.sleep(1)

        vbus = read_vbus()
        #print("vbus after: {}", vbus)
        if vbus > 1.0:
            self.passing = False
            self.add_reason("VBUS discharge (R36P)")
        
        #### run the primary self-test
        self.try_cmd("test factory\r", "|TSTR|DONE") 
        results = self.console.before.decode('utf-8', errors='ignore')
        for line in results.split('\r'):
            if 'TSTR|' in line:
                if self.logfile:
                    self.logfile.write(line.rstrip() + '\n')
                #print(line.rstrip())
                test_output = line.split('|')
                if test_output[2] == 'ECREV':
                    if test_output[3] == 'ffffffff':
                         self.passing = False
                         self.add_reason("U11K/U10K programming failure")
                         return self.passing # severe error, abort test immediately
                    if test_output[3] == 'dddddddd':
                         self.passing = False
                         self.add_reason("U11K/U10K/U10W boot failure")
                         self.add_reason("or U14W/U12W/U17P/U11P I2C fail")
                         return self.passing # severe error, abort test immediately
                if test_output[2] == 'GYRO':
                    if int(test_output[6]) != 0x6A: # id code = 0x6A == LSM6DSLTR; previous rev is 0x69 == LSM6DS3.
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
                    if stats[12] < 3680 or stats[12] > 3740: # battery voltage, according to the gas gauge
                        # battery voltage "brackets high" because we should be charging
                        self.passing = False
                        self.add_reason("U11P BQ27421 fail")
                if test_output[2] == 'USBCC':
                    if int(test_output[5]) != 2:
                        self.passing = False
                        self.add_reason("U16P TUSB320 fail")
                if test_output[2] == 'TRNG':
                    if test_output[3] != 'PASS':
                        self.passing = False
                        if test_output[4] == 'AV0':
                            self.add_reason("U11R/U12R/D11R fail")
                        if test_output[4] == 'AV1':
                            self.add_reason("U11R/U10R/D10R fail")
                        if test_output[4] == 'RO':
                            self.add_reason("U11F Ring Osc fail")
                if test_output[2] == 'VCCINT':
                    if test_output[3] != 'PASS':
                        self.passing = False
                        self.add_reason("VCCINT {} fail (U12F)".format(test_output[4]))
                if test_output[2] == 'VCCAUX':
                    if test_output[3] != 'PASS':
                        self.passing = False
                        self.add_reason("VCCAUX {} fail (U13F)".format(test_output[4]))
                if test_output[2] == 'VCCBRAM':
                    if test_output[3] != 'PASS':
                        self.passing = False
                        self.add_reason("VCCBRAM {} fail (U12F)".format(test_output[4]))
                if test_output[2] == 'ECRESET':
                    if test_output[3] != 'PASS':
                        self.passing = False
                        self.add_reason("ECRESET fail (Q18F/U11K/U10K)")
                        
        with canvas(oled) as draw:
            draw.text((0, 0), "Selftest / Backlight...", fill="white")

        # measure bright backlight
        self.try_cmd("test bl2\r", "|TSTR|BL2", timeout=10) 
        time.sleep(2)

        ibat_bl2 = 0.0
        for i in range(10):
            time.sleep(0.1)
            ibat_bl2 += read_i_bat(high_range=True)
        ibat_bl2 /= 10.0
                                        
        # measure mid-level backlight
        self.try_cmd("test bl1\r", "|TSTR|BL1", timeout=10) 
        time.sleep(2)

        ibat_bl1 = 0.0
        for i in range(10):
            time.sleep(0.1)
            ibat_bl1 += read_i_bat(high_range=True)
        ibat_bl1 /= 10.0

        # turn off backlight
        self.try_cmd("test bl0\r", "|TSTR|BL0", timeout=10) 
        time.sleep(2)

        ibat_nom = 0.0
        for i in range(10):
            time.sleep(0.1)
            ibat_nom += read_i_bat(high_range=True)
        ibat_nom /= 10.0

        if self.logfile:
            self.logfile.write("ibat_bl2: {:.4f}A\n".format(ibat_bl2))
            self.logfile.write("ibat_bl1: {:.4f}A\n".format(ibat_bl1))
            self.logfile.write("ibat_nom: {:.4f}A\n".format(ibat_nom))

        # basic functionality
        if (ibat_bl2 < ibat_bl1) or (ibat_bl1 < ibat_nom):
            self.passing = False
            self.add_reason("Backlight fail / U12W")
            return self.passing
        # check that dimming happens (there is a failure mode where no dimming happens)
        if (ibat_bl2 - ibat_nom) < (ibat_bl1 - ibat_nom) * 2:
            self.passing = False
            self.add_reason("Backlight dimming fail / U12W")
            return self.passing

        ##### test charger
        with canvas(oled) as draw:
            draw.text((0, 0), "Selftest / Charger...", fill="white")
        # turn on VBUS
        GPIO.output(GPIO_ISENSE, 1) # set to "high" range
        GPIO.output(GPIO_VBUS, 1) # this should start charging
        time.sleep(2)
        ibus_chg = 0.0
        for i in range(10):
            time.sleep(0.1)
            ibus_chg += read_i_vbus()
        ibus_chg /= 10.0
        
        GPIO.output(GPIO_ISENSE, 0) # this should cease charging by increasing the battery impedance
        time.sleep(2)
        ibus_nochg = 0.0
        for i in range(10):
            time.sleep(0.1)
            ibus_nochg += read_i_vbus()
        ibus_nochg /= 10.0

        self.logfile.write("charge current: {:.4f}A\n".format(ibus_chg - ibus_nochg))
        if ibus_chg - ibus_nochg < 0.28:
            self.passing = False
            self.add_reason("Charger I-fail / U16P BQ25618")
        
        GPIO.output(GPIO_ISENSE, 1) # "reconnect" the battery
        time.sleep(2)
        GPIO.output(GPIO_VBUS, 0) # finish test powering off of battery

        # we are now on battery power again

        ##### vibe motor test
        with canvas(oled) as draw:
            draw.text((0, 0), "Selftest / Vibe...", fill="white")
        VIBE_HAPPENED=False
        GPIO.add_event_detect(GPIO_VIBE_SENSE, GPIO.FALLING, callback=vibe_callback)
        self.try_cmd("test vibe\r", "|TSTR|VIBE", timeout=10) 
        time.sleep(1)
        GPIO.remove_event_detect(GPIO_VIBE_SENSE)
        if VIBE_HAPPENED == False:
            self.passing = False
            self.add_reason("VIBE did not trigger (Q12U)")

        ##### suspend/resume test
        with canvas(oled) as draw:
            draw.text((0, 0), "Selftest / Suspend...", fill="white")

        # baseline the ibat prior to sleep
        ibat_nom = 0.0
        for i in range(10):
            time.sleep(0.1)
            ibat_nom += read_i_bat(high_range=True)
        ibat_nom /= 10.0
        
        # there is no response from this, so we don't use try_cmd()
        self.slow_send("sleep sus\r")
        time.sleep(3) # should power down within 3 seconds

        ibat_sus = 0.0
        for i in range(10):
            time.sleep(0.1)
            sus = read_i_bat(high_range=True)
            #print("sus current: {:.3f}mA".format(sus))
            ibat_sus += sus
        ibat_sus /= 10.0
        
        GPIO.output(GPIO_VBUS, 1) # resume system by briefly pulsing VBUS
        time.sleep(0.5)
        GPIO.output(GPIO_VBUS, 0)
        
        ibat_post = 0.0
        for i in range(10):
            time.sleep(0.1)
            ibat_post += read_i_bat(high_range=True)
        ibat_post /= 10.0

        if self.logfile:
            self.logfile.write("baseline current: {:.4f}mA\n".format(ibat_nom * 1000))
            self.logfile.write("suspend current : {:.4f}mA\n".format(ibat_sus * 1000))
            self.logfile.write("resume current  : {:.4f}mA\n".format(ibat_post * 1000))
        if ibat_sus > 0.040: # about a 0.020 offset measured on testjig #1
            self.passing = False
            self.add_reason("Suspend leakage high {}mA".format(ibat_sus * 1000))
        if ibat_post < 0.180:
            self.passing = False
            self.add_reason("System did not resume as expected")
            
        time.sleep(2) # just a moment for the resume to fully finish
        
        ##### shipmode test
        with canvas(oled) as draw:
            draw.text((0, 0), "Selftest / Shipmode...", fill="white")
        # there is no response from this, so we don't use try_cmd()
        self.slow_send("sleep ship\r")
        # spec time is 15 seconds max before in ship mode
        did_ship = False
        for x in range(16, 0, -1):
            with canvas(oled) as draw:
                draw.text((0, 0), "Wait for BQ25618...{}".format(x), fill="white")
            time.sleep(1.0)
            if read_i_bat(high_range=True) < 0.005:
                did_ship = True
                break

        if did_ship:
            time.sleep(4.0)
            GPIO.output(GPIO_ISENSE, 0)
            i_ship = 0.0
            for i in range(10):
               time.sleep(0.1)
               i_ship += read_i_bat(high_range=False)
            i_ship /= 10.0
            GPIO.output(GPIO_ISENSE, 1)
            if self.logfile:
                self.logfile.write("ship current: {:.4f}uA\n".format(i_ship * 1000000))
            if i_ship > 300e-6: # about a 70uA offset mesaured on testjig #1
                self.passing = False
                self.add_reason("Ship mode leakage high {}uA".format(i_ship * 1000000))
        else:
            self.passing = False
            self.add_reason("Didn't enter ship mode")

        # self test ends with device in ship mode
        
        with canvas(oled) as draw:
            draw.text((0, 0), "Self test complete!", fill="white")
        time.sleep(1)
        with canvas(oled) as draw:
            oled.clear()

        self.console.close()
        return self.passing
    
