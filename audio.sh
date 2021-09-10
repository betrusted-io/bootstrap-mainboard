#!/bin/sh

if [ ! -d /sys/class/gpio/gpio0 ]
then
    echo "0" > /sys/class/gpio/export
fi
if [ ! -d /sys/class/gpio/gpio5 ]
then
    echo "5" > /sys/class/gpio/export
fi
if [ ! -d /sys/class/gpio/gpio26 ]
then
    echo "26" > /sys/class/gpio/export
fi

echo "out" > /sys/class/gpio/gpio0/direction
echo "out" > /sys/class/gpio/gpio5/direction
echo "out" > /sys/class/gpio/gpio26/direction

# 0 = HPR, 5 = HPL, 26 = SPK
echo "1" > /sys/class/gpio/gpio0/value
echo "0" > /sys/class/gpio/gpio5/value
echo "0" > /sys/class/gpio/gpio26/value

