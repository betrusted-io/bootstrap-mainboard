#!/usr/bin/python3

"""
A script that runs periodically to ensure that the tester is configured correctly
"""

import subprocess
import psutil
import time

from luma.core.render import canvas
from luma.core.interface.serial import bitbang
import RPi.GPIO as GPIO
from luma.oled.device import ssd1322
import luma.oled.device

SCRIPT='factory-firmwar' # the last letters are truncated, because linux sucks

def checkIfProcessRunning(processName):
    '''
    Check if there is any running process that contains the given name processName.
    '''
    #Iterate over the all the running process
    for proc in psutil.process_iter():
        try:
            #print(proc.name())
            # Check if process name contains the given name string.
            if processName.lower() in proc.name().lower():
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    return False;

def killScript(processName):
    for proc in psutil.process_iter():
        if processName in proc.name():
            print(processName + " found in table, killing: " + proc.name())
            proc.kill()

def main():
    global SCRIPT
    oled = ssd1322(bitbang(SCLK=11, SDA=10, CE=7, DC=1, RST=12))
    oled.clear()
    with canvas(oled) as draw:
       draw.text((0, 0), "scriptminder.py started...", fill="White")
    time.sleep(3)
    
    while True:
        if checkIfProcessRunning(SCRIPT):
            print(SCRIPT + " is running, sleeping!")
            time.sleep(3)
        else:
            print(SCRIPT + " is not running, restarting it!")
            killScript(SCRIPT) # just in case, so we don't have multiple copies
            subprocess.run(['/home/pi/code/bootstrap-mainboard/factory-firmware.py'])
            time.sleep(3)
            


if __name__ == '__main__':
   main()
   
