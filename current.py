#!/usr/bin/env python3
import RPi.GPIO as GPIO
from gpiodefs import *

from adc128 import *

global GPIO_START, GPIO_FUNC, GPIO_BSIM, GPIO_ISENSE, GPIO_VBUS, GPIO_UART_SOC
global GPIO_PROG_B, GPIO_AUD_HPR, GPIO_AUD_HPL, GPIO_AUD_SPK
global ADC128_REG, ADC128_DEV0, ADC128_DEV1, ADC_CH

GPIO.setmode(GPIO.BCM)

GPIO.setup(GPIO_VBUS, GPIO.OUT)
GPIO.setup(GPIO_BSIM, GPIO.OUT)
GPIO.setup(GPIO_ISENSE, GPIO.OUT)

vbus = read_vbus()
ibat = read_i_bat(high_range=True)
ibus = read_i_vbus()

print(f"vbus: {vbus}")
print(f"ibat: {ibat}")
print(f"ibus: {ibus}")

