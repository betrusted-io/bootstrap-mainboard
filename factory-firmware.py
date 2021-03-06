#!/usr/bin/python3

"""
Factory test script for the firmware-only burning station
"""

import time # for sleep and timestamps
from datetime import datetime # for deriving human-readable dates for logging
import subprocess
import atexit
import argparse
from luma.core.render import canvas
from luma.core.interface.serial import bitbang
import RPi.GPIO as GPIO
from luma.oled.device import ssd1322
import luma.oled.device

from gpiodefs import *
from adc128 import *

# all this plumbing, just to get my IP address. :-P
import os
import socket
import fcntl
import struct
def get_ip_address(ifname):
     s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
     try:
         addr = socket.inet_ntoa(fcntl.ioctl(
            s.fileno(),
            0x8915, # SIOCGIFADDR
            struct.pack('256s', ifname[:15]) )[20:24])
         return addr
     except:
         return None

oled=None  # global placeholder for the OLED device handle
IN_PROGRESS=False # set to true if a test is in progress
MENU_MODE=False

from tests import *
from tests.BaseTest import BaseTest

def get_tests():
    tests = []
    #tests.append(Zero.Test())
    tests.append(PowerOn.Test())
    
    if True:
       tests.append(FpgaId.Test())
       tests.append(EcFirmware.Test())

       tests.append(SocFirmware.Test())
       
       tests.append(SelfTest.Test())
       tests.append(AudioTest.Test())
       tests.append(AudioBurn.Test())

       tests.append(Kill.Test())
    else:
       #tests.append(SocFirmware.Test())
       #tests.append(SelfTest.Test())
       #tests.append(AudioTest.Test())
       tests.append(Kill.Test())
    
    tests.append(PowerOff.Test())
    return tests

def makeint(i, base=10):
    try:
        return int(i, base=base)
    except:
        return 0
            
def get_gitver():
    major = 0
    minor = 0
    rev = 0
    gitrev = 0
    gitextra = 0
    dirty = 0

    def decode_version(v):
        version = v.split(".")
        major = 0
        minor = 0
        rev = 0
        if len(version) >= 3:
            rev = makeint(version[2])
        if len(version) >= 2:
            minor = makeint(version[1])
        if len(version) >= 1:
            major = makeint(version[0])
        return (major, minor, rev)
    git_rev_cmd = subprocess.Popen(["git", "describe", "--tags", "--long", "--dirty=+", "--abbrev=8"],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE)
    (git_stdout, _) = git_rev_cmd.communicate()
    if git_rev_cmd.wait() != 0:
        print('unable to get git version')
        return (major, minor, rev, gitrev, gitextra, dirty)
    raw_git_rev = git_stdout.decode().strip()

    if raw_git_rev[-1] == "+":
        raw_git_rev = raw_git_rev[:-1]
        dirty = 1

    parts = raw_git_rev.split("-")

    if len(parts) >= 3:
        if parts[0].startswith("v"):
            version = parts[0]
            if version.startswith("v"):
                version = parts[0][1:]
            (major, minor, rev) = decode_version(version)
        gitextra = makeint(parts[1])
        if parts[2].startswith("g"):
            gitrev = makeint(parts[2][1:], base=16)
    elif len(parts) >= 2:
        if parts[1].startswith("g"):
            gitrev = makeint(parts[1][1:], base=16)
        version = parts[0]
        if version.startswith("v"):
            version = parts[0][1:]
        (major, minor, rev) = decode_version(version)
    elif len(parts) >= 1:
        version = parts[0]
        if version.startswith("v"):
            version = parts[0][1:]
        (major, minor, rev) = decode_version(version)

    return (major, minor, rev, gitrev, gitextra, dirty)

def wait_start():
    while GPIO.input(GPIO_START) == GPIO.LOW:
        time.sleep(0.1)
    while GPIO.input(GPIO_START) == GPIO.HIGH:
        time.sleep(0.1)

def abort_callback(channel):
    global IN_PROGRESS
    global MENU_MODE

    if IN_PROGRESS:
        print("Abort button pressed, quitting!".format(channel))
        oled.clear()
        reset_tester_outputs()
        exit(0)
    else:
         # test is not in progress, flag to menu mode
         while GPIO.input(GPIO_FUNC) == GPIO.LOW: # wait for button to be let go
              time.sleep(0.1)
         MENU_MODE=True

def reset_tester_outputs():
    # tristates
    GPIO.setup(GPIO_PROG_B, GPIO.IN)
    GPIO.setup(GPIO_CRESET_N, GPIO.IN)
    # driven
    GPIO.output(GPIO_VBUS, 0)
    GPIO.output(GPIO_BSIM, 0)
    GPIO.output(GPIO_ISENSE, 1)
    GPIO.output(GPIO_UART_SOC, 1)
    GPIO.output(GPIO_AUD_HPR, 0)
    GPIO.output(GPIO_AUD_HPL, 0)
    GPIO.output(GPIO_AUD_SPK, 0)
    GPIO.output(GPIO_DRV_UP5K_N, 1)

# tests is a list of tests
def run_tests(tests, logfile=None):
    global oled
    global environment

    elapsed_start = time.time()
    # each test runs, and can draw onto the screen for status updates
    # they return a simple pass/fail result, and if not passing, the full sequence aborts
    for test in tests:
        test.set_env(environment) # make sure each command has a clean copy of their runtime environment
        test.reset(logfile)     # reset the test state before running it. this also resets the start timer.
        passed = test.run(oled)
        with canvas(oled) as draw:
            draw.text((0, FONT_HEIGHT * 4), "Test: {:.2f}s Total: {:.2f}s".format(time.time() - test.start, time.time() - elapsed_start))
        time.sleep(0.5)
        if logfile:
            logfile.flush()
        if passed != True:
            break
    elapsed = time.time() - elapsed_start

    # print a summary screen
    maxlines = 4
    colwidth = 64
    row = 0
    col = 0
    passing = True
    with canvas(oled) as draw:
        oled.clear()
        for test in tests:
            draw.text((col * colwidth, FONT_HEIGHT * row), test.short_status())
            if test.is_passing() != True:
                passing = False
            row += 1
            if row >= maxlines:
                row = 0
                col += 1

        if passing:
            note = "PASS. Ran for {:.2f}s. Press START.".format(elapsed)
        else:
            note = "FAIL. Ran for {:.2f}s. Press START.".format(elapsed)
        draw.text((0, FONT_HEIGHT * 4), note)
        if logfile:
            logfile.write(note + "\n")
            logfile.flush()

    wait_start()
    
    if passing != True:
        if logfile:
            reasons = test.fail_reasons()
            logfile.write("Fail reasons given:\n")
            for reason in reasons:
                logfile.write(reason + "\n")
            logfile.flush()
        with canvas(oled) as draw:
            for test in tests:
                if test.is_passing() != True:
                    reasons = test.fail_reasons()
                    line = 0
                    for reason in reasons:
                        draw.text((0, FONT_HEIGHT * line), reason)
                        line += 1
                        if line >= maxlines:
                            break
            draw.text((0, FONT_HEIGHT * 4), "Details listed. Press START to continue.")
                        
    wait_start()

def do_shutdown():
    with canvas(oled) as draw:
        draw.text((0, FONT_HEIGHT * 0), "Shutting down, please wait ~30 seconds.")
        draw.text((0, FONT_HEIGHT * 1), "Remove power after the green LED on the")
        draw.text((0, FONT_HEIGHT * 2), "Raspberry Pi blinks ten times, stays on")
        draw.text((0, FONT_HEIGHT * 3), "for a moment, then turns off.")
        draw.text((0, FONT_HEIGHT * 4), "The red LED will continue to stay on.")
    subprocess.run(['sudo', 'shutdown', '-h', 'now'])
    time.sleep(15)

############################# TODO ##########################
def do_update():
    # note to self:
    # updates are done with a 'git pull origin main' and then a 'git submodule update'
    # however we also need to handle the case that the branch was left in a weird state...?
    # would also be nice to relay the subprocess.run() outputs to the screen somehow for review & confirmation
    # and also finally end with a screen that shows the sha2sum of the main script plus key files, so
    # that the factory can take a photo of it and I can confirm things are in fact up to date.
    with canvas(oled) as draw:
        draw.text((0, FONT_HEIGHT * 0), "Updates not yet implemented!")
        draw.text((0, FONT_HEIGHT * 1), "Check back later.")
    time.sleep(3)

def do_return():
     pass

def draw_menu(oled, menu_items, selected):
    with canvas(oled) as draw:
         line = 0
         for (text, func) in menu_items:
             if line == selected:
                draw.text((0, FONT_HEIGHT * line), "> " + text)
             else:
                draw.text((0, FONT_HEIGHT * line), "  " + text)
             line = line + 1

         draw.text((0, FONT_HEIGHT * 4), "FUNC to change, START to select." )

     
def do_menu():
    global FONT_HEIGHT
    global oled
    global MENU_MODE

    MENU_MODE = False

    menu_items = [
         ("Return to main screen", do_return),
         ("Shutdown", do_shutdown ),
         ("Update", do_update ),
    ]
    
    oled.clear()
    selected = 0
    line = 0
    draw_menu(oled, menu_items, selected)
    while True:
        if GPIO.input(GPIO_START) == GPIO.HIGH:
            break
        if MENU_MODE == True:
             MENU_MODE = False
             selected = (selected + 1) % len(menu_items)
             draw_menu(oled, menu_items, selected)
        time.sleep(0.1)
        
    # wait for the operator to let go of the switch
    while GPIO.input(GPIO_START) == GPIO.HIGH:
        time.sleep(0.1)

    (text, func) = menu_items[selected]
    func()
    MENU_MODE = False
    
def main():
    global FONT_HEIGHT
    global GPIO_START, GPIO_FUNC, GPIO_BSIM, GPIO_ISENSE, GPIO_VBUS, GPIO_UART_SOC
    global GPIO_PROG_B, GPIO_AUD_HPR, GPIO_AUD_HPL, GPIO_AUD_SPK
    global oled
    global ADC128_REG, ADC128_DEV0, ADC128_DEV1, ADC_CH
    global IN_PROGRESS
    global MENU_MODE

    parser = argparse.ArgumentParser(description="Precursor Factory Test")
    parser.add_argument(
        "-l", "--log", help="When present, suppress log output to /home/pi/log/", default=True, action="store_false"
    )
    args = parser.parse_args()

    if args.log:
        try:
             logfile = open('/home/pi/log/{:%Y%b%d_%H-%M-%S}.log'.format(datetime.now()), 'w')
        except:
             logfile = None # don't crash if the fs is full, the show must go on!
    else:
        logfile = None
    
    GPIO.setmode(GPIO.BCM)
    
    GPIO.setup(GPIO_START, GPIO.IN)
    GPIO.setup(GPIO_FUNC, GPIO.IN)
    GPIO.setup(GPIO_VIBE_SENSE, GPIO.IN)
    
    GPIO.setup(GPIO_VBUS, GPIO.OUT)
    GPIO.setup(GPIO_BSIM, GPIO.OUT)
    GPIO.setup(GPIO_ISENSE, GPIO.OUT)
    GPIO.setup(GPIO_UART_SOC, GPIO.OUT)
    GPIO.setup(GPIO_PROG_B, GPIO.IN)
    GPIO.setup(GPIO_CRESET_N, GPIO.IN)
    GPIO.setup(GPIO_AUD_HPR, GPIO.OUT)
    GPIO.setup(GPIO_AUD_HPL, GPIO.OUT)
    GPIO.setup(GPIO_AUD_SPK, GPIO.OUT)
    GPIO.setup(GPIO_DRV_UP5K_N, GPIO.OUT)
    reset_tester_outputs()

    init_adc128(oled)
    
    GPIO.add_event_detect(GPIO_FUNC, GPIO.FALLING, callback=abort_callback)

    tests = get_tests()
    
    loops = 0
    oled.show()

    while True:
       reset_tester_outputs()
       IN_PROGRESS=False
       oled.clear()
       (major, minor, rev, gitrev, gitextra, dirty) = get_gitver()
       elapsed = time.time()
       while True:
           if MENU_MODE == False:
               if GPIO.input(GPIO_START) == GPIO.HIGH:
                    IN_PROGRESS=True
                    break;
               if time.time() - elapsed > 1.0:
                    elapsed = time.time()
                    with canvas(oled) as draw:
                       draw.text((0, FONT_HEIGHT * 0), "Tester version {}.{} {:x}+{}".format(major, minor, gitrev, gitextra), fill="white")
                       draw.text((0, FONT_HEIGHT * 1), "Tests run since last abort/restart: {}".format(loops), fill="white")
                       draw.text((0, FONT_HEIGHT * 2), ">>>>> Press START to run test <<<<<", fill="white")
                       draw.text((0, FONT_HEIGHT * 3), "{}".format(str(datetime.now())), fill="white")
                       ipaddr = get_ip_address(b'eth0')
                       if ipaddr != None:
                           draw.text((0, FONT_HEIGHT * 4), "LAN IP address: {}".format(ipaddr), fill="white")
                       else:
                           draw.text((0, FONT_HEIGHT * 4), "*** ERROR: Check LAN cable or Internet! ***")
               time.sleep(0.2)
           else:
                do_menu()

       # wait for the operator to let go of the switch
       while GPIO.input(GPIO_START) == GPIO.HIGH:
           time.sleep(0.1)
                  
       loops += 1
       if logfile:
           logfile.write("------------------------------------------------------------------\n".format(loops, str(datetime.now())))
           logfile.write("Starting run {} at {}\n".format(loops, str(datetime.now())))
           logfile.flush()
       
       run_tests(tests, logfile=logfile)

def cleanup():
    reset_tester_outputs()
    GPIO.cleanup()
    
if __name__ == "__main__":
    global environment
    environment = os.environ.copy() 
    atexit.register(cleanup)
    try:
        print("Tester main loop starting...")
        oled = ssd1322(bitbang(SCLK=11, SDA=10, CE=7, DC=1, RST=12))
        main()
    except KeyboardInterrupt:
        pass
