import time
from luma.core.render import canvas
from luma.core.interface.serial import bitbang
import RPi.GPIO as GPIO
from luma.oled.device import ssd1322
import luma.oled.device
from smbus2 import SMBus

from gpiodefs import *

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

def init_adc128(oled):
    global FONT_HEIGHT
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

def get_adc_ch_dict():
    global ADC_CH

    return ADC_CH

