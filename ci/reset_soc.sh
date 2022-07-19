#!/bin/sh

if [ ! -d /sys/class/gpio/gpio24 ]
then
    echo "24" > /sys/class/gpio/export
fi

sleep 0.1
echo "out" > /sys/class/gpio/gpio24/direction
echo 0 > /sys/class/gpio/gpio24/value
sleep 0.1
echo 1 > /sys/class/gpio/gpio24/value

