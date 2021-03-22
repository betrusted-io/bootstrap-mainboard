#!/usr/bin/python3

"""
Factory test script for the firmware-only burning station
"""

import time
import subprocess
from luma.core.render import canvas
from luma.core.interface.serial import bitbang
import RPi.GPIO as GPIO
from luma.oled.device import ssd1322
import luma.oled.device
from smbus2 import SMBus

FONT_HEIGHT=12
GPIO_START=20   # this is active high
GPIO_FUNC=16    # this is active low
GPIO_BSIM=26    # when high, the battery simulator is powered on
GPIO_ISENSE=37  # when high, current sense mode is high
GPIO_VBUS=21    # when high VBUS is applied to DUT
GPIO_UART_SOC=18 # when high, the UART is routed to the SoC; when low, to the EC
GPIO_PROG_B=24  # when low, the FPGA PROG_B line is asserted
GPIO_AUD_HPR=0  # when high, the right headphone is looped back to the mic
GPIO_AUD_HPL=5  # when high, the left headphone is looped back to the mic
GPIO_AUD_SPK=26 # when high, the speaker output is looped back to the mic
oled=None  # global placeholder for the OLED device handle

def ADC128_REG_IN_MAX(nr):
    return (0x2a + (nr) * 2)

def ADC128_REG_IN_MIN(nr): 
    return (0x2b + (nr) * 2)

def ADC128_REG_IN(nr):
    return (0x20 + (nr))

ADC128_DEV0 = 0x1D
ADC128_DEV1 = 0x37

ADC_CH = {
    "+1.8V_T"   : (0x0 << 8 | 0x0),
    "+1.8V_SBY" : (0x0 << 8 | 0x1),
    "+1.2V_EC"  : (0x0 << 8 | 0x2),
    "+2.5V_EC"  : (0x0 << 8 | 0x3),
    "+3.3V"     : (0x0 << 8 | 0x4),
    "+1.5V_AES" : (0x0 << 8 | 0x5),
    "+3.3VA"    : (0x0 << 8 | 0x6),
    "+V_AVA"    : (0x0 << 8 | 0x7),

    "+1.8V_U"   : (0x1 << 8 | 0x0),
    "+0.95V"    : (0x1 << 8 | 0x1),
    "+5V_LCD"   : (0x1 << 8 | 0x2),
    "V_BL"      : (0x1 << 8 | 0x3),
    "VBUS"      : (0x1 << 8 | 0x4),
    #"NC"       : (0x1 << 8 | 0x5),
    "IBAT"      : (0x1 << 8 | 0x6),
    "IVBUS"     : (0x1 << 8 | 0x7),
}

ADC128 = {
   "TEMP": 0x27,
   "TEMP_MAX": 0x38,
   "TEMP_HYST": 0x39,

   "CONFIG": 0x00,
   "ALARM": 0x01,
   "MASK": 0x03,
   "CONV_RATE": 0x07,
   "DISABLE": 0x08,
   "ONESHOT": 0x09,
   "SHUTDOWN": 0x0a,
   "CONFIG_ADV": 0x0b,
   "BUSY_STATUS": 0x0c,

   "MAN_ID": 0x3e,
   "REV_ID": 0x3f,
}

def init_adc128():
    global oled, FONT_HEIGHT
    global ADC128_REG, ADC128_DEV0, ADC128_DEV1
    
    with canvas(oled) as draw:
        oled.clear()
        line = 0
        with SMBus(1) as i2c:
            # check converter chip IDs
            id = i2c.read_byte_data(ADC128_DEV0, ADC128["MAN_ID"])
            if id != 1:
                draw.text((0, FONT_HEIGHT * line), "ADC128 0 mfg ID mismatch: 0x{:x}".format(id))
                line += 1
            id = i2c.read_byte_data(ADC128_DEV1, ADC128["MAN_ID"])
            if id != 1:
                draw.text((0, FONT_HEIGHT * line), "ADC128 1 mfg ID mismatch: 0x{:x}".format(id))
                line += 1

            id = i2c.read_byte_data(ADC128_DEV0, ADC128["REV_ID"])
            if id != 9:
                draw.text((0, FONT_HEIGHT * line), "ADC128 0 rev ID mismatch: 0x{:x}".format(id))
                line += 1
            id = i2c.read_byte_data(ADC128_DEV1, ADC128["REV_ID"])
            if id != 9:
                draw.text((0, FONT_HEIGHT * line), "ADC128 1 rev ID mismatch: 0x{:x}".format(id))
                line += 1

            # wait for converters to initialize
            while True:
                if (i2c.read_byte_data(ADC128_DEV0, ADC128["BUSY_STATUS"]) & 0x2) == 0:
                    break;
            while True:
                if (i2c.read_byte_data(ADC128_DEV1, ADC128["BUSY_STATUS"]) & 0x2) == 0:
                    break;

            # put chips in shutdown to allow for programming
            i2c.write_byte_data(ADC128_DEV0, ADC128["CONFIG"], 0)
            i2c.write_byte_data(ADC128_DEV1, ADC128["CONFIG"], 0)

            # select internal VREF, and "mode 1" (all single ended inputs active)
            i2c.write_byte_data(ADC128_DEV0, ADC128["CONFIG_ADV"], 1 << 1)
            i2c.write_byte_data(ADC128_DEV1, ADC128["CONFIG_ADV"], 1 << 1)

            # set conversion rate to continuous
            i2c.write_byte_data(ADC128_DEV0, ADC128["CONV_RATE"], 1)
            i2c.write_byte_data(ADC128_DEV1, ADC128["CONV_RATE"], 1)

            # set disable to 0 on used channels
            i2c.write_byte_data(ADC128_DEV0, ADC128["DISABLE"], 0)
            i2c.write_byte_data(ADC128_DEV1, ADC128["DISABLE"], 0x20) # 0010_0000, channel 5 not used

            # startup converter & enable interrupts
            i2c.write_byte_data(ADC128_DEV0, ADC128["CONFIG"], 3)
            i2c.write_byte_data(ADC128_DEV1, ADC128["CONFIG"], 3)
            
            # make sure both converters finish their power-up sequence before continuing
            while True:
                if (i2c.read_byte_data(ADC128_DEV0, ADC128["BUSY_STATUS"]) & 0x2) == 0:
                    break;
            while True:
                if (i2c.read_byte_data(ADC128_DEV1, ADC128["BUSY_STATUS"]) & 0x2) == 0:
                    break;

            draw.text((0, FONT_HEIGHT * line), "ADC128 initialized...")
            time.sleep(0.25) # empirically this was required from a previous implementation, so we copy it over
            time.sleep(1) # some extra time for the mesage to be read, why not

def read_adc128(channel):
    global ADC128_REG, ADC128_DEV0, ADC128_DEV1
    if channel & 0x100:
        device_address = ADC128_DEV1
    else:
        device_address = ADC128_DEV0
        
    with SMBus(1) as i2c:
        i2c.pec = 1 # enable packet error checking
        temp = i2c.read_i2c_block_data(device_address, ADC128_REG_IN(channel & 0xff), 2)
        return (temp[1] & 0xff) | ((temp[0] & 0xff) << 8) >> 4

def read_vbus():
    global ADC_CH
    return (read_adc128(ADC_CH["VBUS"]) * 0.625) / 232.5

def read_i_bat(high_range=True):
    global ADC_CH
    global GPIO_ISENSE
    if high_range:
        GPIO.output(GPIO_ISENSE, 1)
        time.sleep(0.1) # let it settle
        return (read_adc128(ADC_CH["IBAT"]) * 0.0003125)
    else:
        GPIO.output(GPIO_ISENSE, 0)
        time.sleep(0.1)
        return (read_adc128(ADC_CH["IBAT"]) * 0.00000142)
            
def read_i_vbus():
    global ADC_CH
    return (read_adc128(ADC_CH["IVBUS"]) * 0.0003125)
    
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

def abort_callback(channel):
    # this should cause the loop to restart from the top, for now, we use it to exit
    print("Abort button pressed, quitting!".format(channel))
    oled.clear()
    time.sleep(0.2)
    (major, minor, rev, gitrev, gitextra, dirty) = get_gitver()
    with canvas(oled) as draw:
       draw.text((0, FONT_HEIGHT * 0), "Tester version {}.{} {:x}+{}".format(major, minor, gitrev, gitextra), fill="white")
       draw.text((0, FONT_HEIGHT * 2), "Quit pressed, no program running.", fill="white")
    time.sleep(0.2)
    GPIO.cleanup()
    exit(0)

def reset_tester_outputs():
    GPIO.output(GPIO_VBUS, 0)
    GPIO.output(GPIO_BSIM, 0)
    GPIO.output(GPIO_ISENSE, 1)
    GPIO.output(GPIO_UART_SOC, 1)
    GPIO.output(GPIO_PROG_B, 1)
    GPIO.output(GPIO_AUD_HPR, 0)
    GPIO.output(GPIO_AUD_HPL, 0)
    GPIO.output(GPIO_AUD_SPK, 0)

def run_test():
    global FONT_HEIGHT
    global GPIO_START, GPIO_FUNC, GPIO_BSIM, GPIO_ISENSE, GPIO_VBUS, GPIO_UART_SOC
    global GPIO_PROG_B, GPIO_AUD_HPR, GPIO_AUD_HPL, GPIO_AUD_SPK
    global oled
    global ADC128_REG, ADC128_DEV0, ADC128_DEV1, ADC_CH

    # turn on the power
    GPIO.output(GPIO_VBUS, 1)
    GPIO.output(GPIO_BSIM, 1)
    time.sleep(0.5) # wait for power to stabilize
    
    oled.clear()
    with canvas(oled) as draw:
        line = 0
        draw.text((0, FONT_HEIGHT * line), "Measuring current...")
        time.sleep(5)
        
    with canvas(oled) as draw:
        vbus = read_vbus()
        ibat = read_i_bat(high_range=True)
        ibus = read_i_vbus()
        line = 0
        draw.text((0, FONT_HEIGHT * line), "VBUS: {:.3f}V".format(vbus))
        line += 1
        draw.text((0, FONT_HEIGHT * line), "IBUS: {:.3f}mA".format(ibus * 1000))
        line += 1
        draw.text((0, FONT_HEIGHT * line), "IBAT: {:.3f}mA".format(ibat * 1000))
        line += 1
        draw.text((0, FONT_HEIGHT * line), "Press START to continue")

    # turn off the power
    GPIO.output(GPIO_VBUS, 0)
    GPIO.output(GPIO_BSIM, 0)
    while GPIO.input(GPIO_START) == GPIO.LOW:
        time.sleep(0.1)

    
def main():
    global FONT_HEIGHT
    global GPIO_START, GPIO_FUNC, GPIO_BSIM, GPIO_ISENSE, GPIO_VBUS, GPIO_UART_SOC
    global GPIO_PROG_B, GPIO_AUD_HPR, GPIO_AUD_HPL, GPIO_AUD_SPK
    global oled
    global ADC128_REG, ADC128_DEV0, ADC128_DEV1, ADC_CH

    GPIO.setmode(GPIO.BCM)
    
    GPIO.setup(GPIO_START, GPIO.IN)
    GPIO.setup(GPIO_FUNC, GPIO.IN)
    
    GPIO.setup(GPIO_VBUS, GPIO.OUT)
    GPIO.setup(GPIO_BSIM, GPIO.OUT)
    GPIO.setup(GPIO_ISENSE, GPIO.OUT)
    GPIO.setup(GPIO_UART_SOC, GPIO.OUT)
    GPIO.setup(GPIO_PROG_B, GPIO.OUT)
    GPIO.setup(GPIO_AUD_HPR, GPIO.OUT)
    GPIO.setup(GPIO_AUD_HPL, GPIO.OUT)
    GPIO.setup(GPIO_AUD_SPK, GPIO.OUT)
    reset_tester_outputs()

    init_adc128()
    
    GPIO.add_event_detect(GPIO_FUNC, GPIO.FALLING, callback=abort_callback)
    
    loops = 0
    oled.show()

    while True:
       reset_tester_outputs()
       oled.clear()
       (major, minor, rev, gitrev, gitextra, dirty) = get_gitver()
       with canvas(oled) as draw:
          draw.text((0, FONT_HEIGHT * 0), "Tester version {}.{} {:x}+{}".format(major, minor, gitrev, gitextra), fill="white")
          draw.text((0, FONT_HEIGHT * 1), "Tests run since last abort/restart: {}".format(loops), fill="white")
          draw.text((0, FONT_HEIGHT * 2), "Press START to continue...", fill="white")

       while GPIO.input(GPIO_START) == GPIO.LOW:
          time.sleep(0.1)
       loops += 1
       
       run_test()
    
if __name__ == "__main__":
    try:
        print("Tester main loop starting...")
        oled = ssd1322(bitbang(SCLK=11, SDA=10, CE=7, DC=1, RST=12))
        main()
    except KeyboardInterrupt:
        pass
        
    GPIO.cleanup()
