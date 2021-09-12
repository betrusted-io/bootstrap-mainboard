#!/bin/sh

if [ "$1" != "0" ] && [ "$1" != "1" ]; then
    echo "Needs an argument of 0 or 1"
    exit 0
fi

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

sleep 0.1
echo "out" > /sys/class/gpio/gpio26/direction
echo $1 > /sys/class/gpio/gpio26/value
