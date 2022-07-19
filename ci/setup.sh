#!/bin/sh

# set the baud rate
stty -F /dev/ttyS0 115200
# setup the reset pin
if [ ! -d /sys/class/gpio/gpio24 ]
then
    echo "24" > /sys/class/gpio/export
fi
# not in reset
echo 1 > /sys/class/gpio/gpio24/value

# power on the battery simulator
if [ ! -d /sys/class/gpio/gpio26 ]
then
    echo "26" > /sys/class/gpio/export
fi
if [ ! -d /sys/class/gpio/gpio19 ]
then
    echo "19" > /sys/class/gpio/export
fi

# select high current sense position
echo "out" > /sys/class/gpio/gpio19/direction
echo "1" > /sys/class/gpio/gpio19/value
# turn on the simulator
sleep 0.1
echo "out" > /sys/class/gpio/gpio26/direction
echo 1 > /sys/class/gpio/gpio26/value
sleep 0.5

# power on VBUS
if [ ! -d /sys/class/gpio/gpio21 ]
then
    echo "21" > /sys/class/gpio/export
fi
echo "out" > /sys/class/gpio/gpio21/direction
echo 1 > /sys/class/gpio/gpio21/value

sleep 0.5

# system should now be powered on

