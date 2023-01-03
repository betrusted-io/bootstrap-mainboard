#!/bin/sh

# Turn off the battery simulator first to avoid any kickback on the
# buck/boost regulator as the load is suddely cut.

# power off the battery simulator
if [ ! -d /sys/class/gpio/gpio26 ]
then
    echo "26" > /sys/class/gpio/export
fi
if [ ! -d /sys/class/gpio/gpio19 ]
then
    echo "19" > /sys/class/gpio/export
fi

# turn off the simulator
sleep 0.1
echo "out" > /sys/class/gpio/gpio26/direction
echo 0 > /sys/class/gpio/gpio26/value
sleep 1.5

# power off VBUS
if [ ! -d /sys/class/gpio/gpio21 ]
then
    echo "21" > /sys/class/gpio/export
fi
echo "out" > /sys/class/gpio/gpio21/direction
echo 0 > /sys/class/gpio/gpio21/value

sleep 0.5

# system should now be powered off
