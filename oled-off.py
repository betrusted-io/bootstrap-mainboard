#!/usr/bin/python3

from luma.core.render import canvas
from luma.core.interface.serial import bitbang
from luma.oled.device import ssd1322
import luma.oled.device

oled = ssd1322(bitbang(SCLK=11, SDA=10, CE=7, DC=1, RST=12))
oled.clear()
