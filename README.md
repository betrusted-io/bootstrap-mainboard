# Bootstrap Mainboard

A collection of scripts to bootstrap a factory-new or bricked Precursor.

Also includes factory test scripts, to be run on the factory test jig.

## Dependencies

These scripts are assumed to be run on a Raspberry Pi with a RaspiOS "buster" image
(initially tested against Jan 11 2021 release on a Pi 3B+). Compatibility is not
guaranteed for a Pi 4, but it "should" work.

Most of the dependencies are cloned in as submodules, but for select applications
you may want to install more:

- GDB debugging and USB updates: [wishbone-utils](https://github.com/betrusted-io/wishbone-utils).
  Requires Rust to build, but you should also be able to get the pre-built
  [Releases](https://github.com/litex-hub/wishbone-utils/releases) to work for GDB debugging (but not USB updates).
  Note: you can also plug the USB-C port directly into your host, in which case you would
  need the `wishbone-utils` on your host, not the Rpi with debug HAT. x86-hosted `wishbone-utils`
  is actually the more typical use case.
- Factory test: [Luma OLED](https://luma-oled.readthedocs.io/en/latest/software.html). Generally,
  you don't want to run the factory test, as you don't have the rather expensive accompanying
  PCB with all the sensors and adapters to make it work.
  - `pip3 install psutil` -- for the scriptminder.py routine
  
