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

import base64
import subprocess
try:
    import numpy as np
except:
    subprocess.Popen(["sudo", "/usr/bin/pip3", "install", "numpy"])
finally:
    import numpy as np
import math


SAMPLE_RATE = 8000.0
ANALYSIS_DELTA = 20.0 # wider window because cos generation is approximate (originally 10.0Hz)
def analyze(spectrum, target):
    total_power = 0.0
    h1_power = 0.0
    h2_power = 0.0
    outside_power = 0.0
    for (freq, power) in spectrum.items():
        total_power += power
        if (freq >= (target - ANALYSIS_DELTA)) & (freq <= (target + ANALYSIS_DELTA)):
            h1_power += power
        elif (freq >= (target * 2.0 - ANALYSIS_DELTA)) & (freq <= (target * 2.0 + ANALYSIS_DELTA)):
            h2_power += power
        else:
            outside_power += power
    if outside_power > 0.0:
        ratio = (h1_power + h2_power) / outside_power
    else:
        1_000_000.0
    return ratio

def db_compute(samples):
    cum = 0.0
    for sample in samples:
        cum += sample
    mid = cum / float(len(samples))
    cum = 0.0
    for sample in samples:
        a = sample - mid
        cum += (a * a)
    cum /= float(len(samples))
    db = 10.0 * math.log10(cum)
    return db

def ascii_plot(spectrum, logfile):
    SLOTS_PER_BIN=20
    label = 0.0
    total_power = 0.0
    index = 0
    norm = 40.0 / max(spectrum.values())
    for (freq, power) in spectrum.items():
        total_power += power
        if index % SLOTS_PER_BIN == SLOTS_PER_BIN // 2:
            label = freq
        index += 1
        if index % SLOTS_PER_BIN == 0:
            logfile.write('{:6.1f} '.format(label) + '*' * (int(total_power * norm)) + '\n')
            total_power = 0.0
        if freq > 700.0:
            break

def extract_samples(raw_data):
    samples = bytearray()
    index = 0
    for line in raw_data.split('\r'):
        if 'TSTR|' in line:
            parse = line.split('|')
            if int(parse[3]) != index:
                print("Warning: base64 index out of sync\n")
            samples += base64.b64decode(parse[4])
            index += 1
            if index == 32:
                break
    if index != 32:
        print("Warning: missing audio data\n")

    right_samps = []
    for i in range(0, len(samples), 2):
        if i % 4 == 0:
            right_samps.append(float(int.from_bytes(samples[i:i+2], 'little', signed=True)))

    signal = np.array(right_samps, dtype=float)
    return(signal)

def fft(signal):
    data = np.fft.rfft(signal)
    data = data[:-1]
    # for dB
    # data = np.log10(np.sqrt(np.real(data)**2 + np.imag(data)**2) / n) * 10
    # for linear
    data = np.sqrt(np.real(data)**2 + np.imag(data)**2) / len(data)

    results = {}
    freq = 0.0
    for d in data:
        results[freq] = d
        freq += SAMPLE_RATE * 0.5 / float(len(data))
    return results

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

    def automate_analysis(self, results, target_freq):
        signal = extract_samples(results)
        spectrum = fft(signal)
        ratio = analyze(spectrum, target_freq)
        self.logfile.write("Power ratio @ {}Hz: {}\n".format(target_freq, ratio))
        db = db_compute(signal)
        self.logfile.write("dB: {}\n".format(db))
        ascii_plot(spectrum, self.logfile)
        # Power ratio typical range 0.35 (speaker) to 3.5 (headphones)
        # speaker has a wider spectrum because we don't have a filter on the PWM,
        # so there are sampling issues feeding it back into the mic
        # db typical <10 (silence) to 78 (full amplitude)
        if (ratio > 0.25) and (db > 60.0):
            return True
        else:
            return False

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

        time.sleep(9) # give a little time for the device to boot

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

        # Uncomment these lines when testing a provisioned unit that already has a PDDB setup
        # self.slow_send("test\r") # enters password
        # time.sleep(6) # waits for mount
        
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
        if self.automate_analysis(results, 261.63) is False:
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
        if self.automate_analysis(results, 329.63) is False:
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
        if self.automate_analysis(results, 440.0) is False:
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
        if self.automate_analysis(results, 523.25) is True:  # we expect this test to FAIL; should be silence in this config
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

