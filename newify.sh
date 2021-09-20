#!/bin/bash

echo "power on"
sudo ./bsim.sh 1
sleep 0.5
sudo betrusted-scripts/vbus.sh 1

echo "erasing SOC flash"
cd betrusted-scripts/jtag-tools && ./jtag_gpio.py -f pecursors/blank.bin --erase -a 0 --erase-len=0xf80000 -r

cd ../..

echo "erasing EC flash"
sudo fomu-flash/fomu-flash -w precursors/blank.bin

echo "power off"
sudo betrusted-scripts/vbus.sh 0
sleep 0.5
sudo ./bsim.sh 0

