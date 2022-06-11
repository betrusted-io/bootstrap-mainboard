#!/bin/bash
set -e

echo "THIS SCRIPT ASSUMES YOU KNOW WHAT YOU ARE DOING."

echo "power on"
sudo ../bsim.sh 1
sleep 0.5
sudo ../betrusted-scripts/vbus.sh 1

# this pre-supposes the device was functional, so we can run this erase script
sleep 10
echo "erasing PDDB - assuming device was previously tested/functional"
../betrusted-scripts/usb_update.py --erase-pddb
sleep 1

echo "erasing SOC flash"
cd ../betrusted-scripts/jtag-tools && ./jtag_gpio.py -f precursors/blank.bin --erase -a 0 --erase-len=0xf80000 -r

cd ..
cd ..

echo "erasing EC flash"
sudo fomu-flash/fomu-flash -w precursors/blank.bin

sleep 2

echo "power off"
sudo betrusted-scripts/vbus.sh 0
sleep 0.5
sudo ./bsim.sh 0

