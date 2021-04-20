#!/usr/bin/python3

"""
Factory test script for the firmware-only burning station
"""

import time # for sleep and timestamps
from datetime import datetime # for deriving human-readable dates for logging
import subprocess
import atexit
import argparse
import RPi.GPIO as GPIO

from gpiodefs import *
import serial

def cleanup():
    reset_tester_outputs()
    GPIO.cleanup()

def reset_tester_outputs():
    # tristates
    GPIO.setup(GPIO_PROG_B, GPIO.IN)
    GPIO.setup(GPIO_CRESET_N, GPIO.IN)
    # driven
    GPIO.output(GPIO_VBUS, 0)
    GPIO.output(GPIO_UART_SOC, 1)
    GPIO.output(GPIO_DRV_UP5K_N, 1)

    GPIO.output(GPIO_UP5K_MOSI, 0)
    GPIO.output(GPIO_UP5K_SCK, 0)
    GPIO.output(GPIO_UP5K_CSN, 0)

    GPIO.output(GPIO_JTAG_TCK, 0)
    GPIO.output(GPIO_JTAG_TMS, 0)
    GPIO.output(GPIO_JTAG_TDI, 0)

def check_tdi():
    passing = True
    for i in range(10):
       GPIO.output(GPIO_JTAG_TDI, 0)
       if GPIO.input(GPIO_JTAG_TDO) != GPIO.LOW:
           passing = False
           
       GPIO.output(GPIO_JTAG_TDI, 1)
       if GPIO.input(GPIO_JTAG_TDO) != GPIO.HIGH:
           passing = False

    return passing

def render_result(code):
    #####################
    ##### TODO: add PASS/FAIL LED outputs
    #####################
    
    # alternate fast flashing if pass
    if code == True:
        for i in range(6):
            GPIO.setup(GPIO_PROG_B, GPIO.OUT)
            GPIO.output(GPIO_PROG_B, 0)
            time.sleep(0.2)
            GPIO.setup(GPIO_PROG_B, GPIO.IN)

            GPIO.setup(GPIO_CRESET_N, GPIO.OUT)
            GPIO.output(GPIO_CRESET_N, 0)
            time.sleep(0.2)
            GPIO.setup(GPIO_CRESET_N, GPIO.IN)
    # simultaneous slow flashing if fail
    else:
        for i in range(3):
            GPIO.setup(GPIO_PROG_B, GPIO.OUT)
            GPIO.output(GPIO_PROG_B, 0)
            GPIO.setup(GPIO_CRESET_N, GPIO.OUT)
            GPIO.output(GPIO_CRESET_N, 0)
            time.sleep(1.0)
            GPIO.setup(GPIO_PROG_B, GPIO.IN)
            GPIO.setup(GPIO_CRESET_N, GPIO.IN)
            time.sleep(1.0)
            
    GPIO.setup(GPIO_PROG_B, GPIO.IN)
    GPIO.setup(GPIO_CRESET_N, GPIO.IN)

def shift_clk(port):
    port.write(bytes([0xF0]))
    port.read(1)  # this is essential, otherwise clocks don't flush. Throw away the read back value.
    #port.flush() # this is way too slow.

def check_pattern(port, pattern):
    jtag_tdi  = (pattern >> 0) & 1
    jtag_tck  = (pattern >> 1) & 1
    jtag_tms  = (pattern >> 2) & 1
    up5k_mosi = (pattern >> 3) & 1
    up5k_sck  = (pattern >> 4) & 1
    
    GPIO.output(GPIO_JTAG_TDI,    jtag_tdi)
    GPIO.output(GPIO_JTAG_TCK,    jtag_tck)
    GPIO.output(GPIO_JTAG_TMS,    jtag_tms)
    GPIO.output(GPIO_UP5K_MOSI,   up5k_mosi)
    GPIO.output(GPIO_UP5K_SCK,    up5k_sck)

    GPIO.output(GPIO_UP5K_CSN, 0) # load the pattern
    GPIO.output(GPIO_UP5K_CSN, 1) # it's asynchronous, so it just needs a short pulse to load the pattern

    # just unroll the damn loop, it's not fancy, but it is easier to read this way
    # H input is always zero
    if GPIO.input(GPIO_UP5K_MISO) != GPIO.LOW:
        return(["CHECK: H input not low"])
    shift_clk(port) # advance the MISO output from  H->G
    # G input is UP5K_SCLK
    if GPIO.input(GPIO_UP5K_MISO) != up5k_sck:
        return(["CHECK: SCK mismatch"])
    shift_clk(port)
    # F input is always zero
    if GPIO.input(GPIO_UP5K_MISO) != GPIO.LOW:
        return(["CHECK: F input not low"])
    shift_clk(port)
    # E input is always zero
    if GPIO.input(GPIO_UP5K_MISO) != GPIO.LOW:
        return(["CHECK: E input not low"])
    shift_clk(port)
    # D input is MOSI
    if GPIO.input(GPIO_UP5K_MISO) != up5k_mosi:
        return(["CHECK: UP5K MOSI mismatch"])
    shift_clk(port)
    # C input is TMS
    if GPIO.input(GPIO_UP5K_MISO) != jtag_tms:
        return(["CHECK: JTAG TMS mismatch"])
    shift_clk(port)
    # B input is TCK
    if GPIO.input(GPIO_UP5K_MISO) != jtag_tck:
        return(["CHECK: JTAG TCK mismatch"])
    shift_clk(port)
    # A input is TDI
    if GPIO.input(GPIO_UP5K_MISO) != jtag_tdi:
        return(["CHECK: JTAG TDI mismatch"])
    shift_clk(port)
    # end chain is always 0
    if GPIO.input(GPIO_UP5K_MISO) != GPIO.LOW:
        return(["CHECK: End chain not low"])

    return None
    
def check_shift(port):
    reasons = []
    max_reasons = 16

    # assume: power is on
    # make sure we are in FPGA UART mode
    GPIO.output(GPIO_UART_SOC, 1)

    # first shift to zero and check that we have an all-zero shift
    GPIO.output(GPIO_UP5K_CSN, 1) # puts it in shift mode
    for i in range(8):
        shift_clk(port)
    if GPIO.input(GPIO_UP5K_MISO) != GPIO.LOW:
        reasons.append(["SHIFT: zero check failed"])

    for pat in range(32): # 32 possible patterns, check all of them
        r = check_pattern(port, pat)
        if r != None:
            if len(reasons) < max_reasons:
                reasons.append("SHIFT: iter {} | {}".format(pat, r))
            elif len(reasons) == max_reasons:
                reasons.append("SHIFT: too many errors, truncating!")
    
    if len(reasons) == 0:
        #print("SHIFT: passed")
        return None
    else:
        #print("SHIFT: failed {}".format(reasons))
        return reasons
    
def check_serial(port):
    passing = True

    # first check the UP5K loop, with the power off
    # power is off under the theory that if it's still actually looped to the FPGA path,
    # the level translators would not work and we'd see that error
    GPIO.output(GPIO_VBUS, 0)
    time.sleep(0.3) # should already be off so we can shorten this
    GPIO.output(GPIO_UART_SOC, 0)
    test_string = b"This is a test of the UP5K loopback path\n\r"
    port.write(test_string)
    rcv = port.read(len(test_string))
    print("Serial port test got: " + rcv.decode('utf-8', 'backslashreplace'))
    if rcv != test_string:
        passing = False

    # now put it into FPGA mode with power on
    GPIO.output(GPIO_VBUS, 1)
    time.sleep(0.4)
    GPIO.output(GPIO_UART_SOC, 1)
    test_string = b"This is a test of the FPGA loopback path\n\r"
    port.write(test_string)
    rcv = port.read(len(test_string))
    print("Serial port test got: " + rcv.decode('utf-8', 'backslashreplace'))
    if rcv != test_string:
        passing = False

    return passing
    
def main():
    global GPIO_START, GPIO_FUNC, GPIO_BSIM, GPIO_ISENSE, GPIO_VBUS, GPIO_UART_SOC
    global GPIO_PROG_B, GPIO_AUD_HPR, GPIO_AUD_HPL, GPIO_AUD_SPK

    parser = argparse.ArgumentParser(description="Precursor HAT Test")
    parser.add_argument(
        "-l", "--log", help="When present, suppress log output to /home/pi/log/", default=True, action="store_false"
    )
    args = parser.parse_args()

    if args.log:
        try:
             logfile = open('/home/precursor/log/hat_{:%Y%b%d_%H-%M-%S}.log'.format(datetime.now()), 'w')
        except:
             logfile = None # don't crash if the fs is full, the show must go on!
    else:
        logfile = None
    
    GPIO.setmode(GPIO.BCM)
    
    GPIO.setup(GPIO_VBUS, GPIO.OUT)
    GPIO.setup(GPIO_UART_SOC, GPIO.OUT)
    GPIO.setup(GPIO_PROG_B, GPIO.IN)
    GPIO.setup(GPIO_CRESET_N, GPIO.IN)

    GPIO.setup(GPIO_DRV_UP5K_N, GPIO.OUT)
    GPIO.setup(GPIO_UP5K_MOSI, GPIO.OUT)
    GPIO.setup(GPIO_UP5K_MISO, GPIO.IN)
    GPIO.setup(GPIO_UP5K_SCK, GPIO.OUT)
    GPIO.setup(GPIO_UP5K_CSN, GPIO.OUT)
    GPIO.setup(GPIO_JTAG_TCK, GPIO.OUT)
    GPIO.setup(GPIO_JTAG_TMS, GPIO.OUT)
    GPIO.setup(GPIO_JTAG_TDO, GPIO.IN)
    GPIO.setup(GPIO_JTAG_TDI, GPIO.OUT)
    
    reset_tester_outputs()

    port = serial.Serial("/dev/ttyAMA0", baudrate=115200, timeout=0.5)

    #####################
    ##### TODO: add a "tester ready" LED output
    #####################
    
    test_status = True
    first_run = True
    while True:
        # this is at the top because we want the "continue" abort to print a message
        if first_run == False:
            if test_status == True:
                print("HAT test PASS")
                if logfile:
                    logfile.write("{}: HAT test PASS\n".format(str(datetime.now())))
                    logfile.flush()
            else:
                print("HAT test FAIL:")
                for reason in reasons:
                    print("  " + str(reason))
                if logfile:
                    logfile.write("{}: HAT test FAIL\n".format(str(datetime.now())))
                    for reason in reasons:
                        logfile.write("  {}\n".format(str(reason)))
                    logfile.flush()
            render_result(test_status)
            
            ##### power off the device
            GPIO.output(GPIO_VBUS, 0)
        else:
            first_run = False
        
        test_status = True
        reasons = []
        
        reset_tester_outputs()

        #####################
        ##### TODO: replace this input with a button press on the test jig
        #####################
        input("Press enter to continue...")
        #####################
        ##### TODO: add a "test running" LED output
        #####################
        
        port.reset_input_buffer()
        port.reset_output_buffer()
        ##### test the serial port. This will control the power, so don't need to set it ourselves.
        if check_serial(port) != True:
            test_status = False
            reasons.append(["Serial port fail"])
            continue  # don't run any other tests if the serial port doesn't work!

        ##### power on the device
        GPIO.output(GPIO_VBUS, 1) # this is just a preventative power-on, it should already be on...
        time.sleep(0.1)

        ##### check the TDI loopback
        if check_tdi() != True:
            test_status = False
            reasons.append(["JTAG TDI/TDO loop fail"])

        ##### check that drive works by not asserting it, running a test, and expecting errors.
        GPIO.output(GPIO_DRV_UP5K_N, 1)
        result = check_shift(port)
        if result == None: # we /expect/ errors if this is not asserted
            test_status = False
            reasons.append(["DRV_UP5K_N test failed"])

        ##### check all the other GPIOs
        GPIO.output(GPIO_DRV_UP5K_N, 0)
        result = check_shift(port)
        if result != None:
            test_status = False
            for r in result:
               reasons.append(r)
        GPIO.output(GPIO_DRV_UP5K_N, 1)


if __name__ == "__main__":
    atexit.register(cleanup)
    try:
        print("Tester main loop starting...")
        main()
    except KeyboardInterrupt:
        pass
