#!/bin/bash
set -e

echo "THIS SCRIPT ASSUMES YOU KNOW WHAT YOU ARE DOING."

echo "power on"
sudo ../bsim.sh 1
sleep 0.5
sudo ../betrusted-scripts/vbus.sh 1

# this pre-supposes the device was functional, so we can run this erase script
sleep 10

# check to see if the device is listed in usb -- if not, it's possible we're starting from a device
# that was already "newified", in which case we should skip the USB steps.
DEV_PRESENT=`lsusb | grep "1209:5bf0" | wc -l`

if [[ $DEV_PRESENT -eq 1 ]]
then
    echo "erasing PDDB - assuming device was previously tested/functional"
    ../betrusted-scripts/usb_update.py --erase-pddb
    sleep 1

    echo "erasing SOC flash"
    cd ../betrusted-scripts/jtag-tools && ./jtag_gpio.py -f precursors/blank.bin --erase -a 0 --erase-len=0xf80000 -r

    cd ..
else
    echo "No device found -- assuming it was previously newified, and there is no SoC. Skipping USB steps."
fi

cd ..

echo "erasing EC flash"
sudo fomu-flash/fomu-flash -w precursors/blank.bin

sleep 2

echo "power off"
sudo betrusted-scripts/vbus.sh 0
sleep 0.5
sudo ./bsim.sh 0

