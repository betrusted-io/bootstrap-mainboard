#!/usr/bin/python3

"""
Factory test script for the firmware-only burning station
"""

import time
import subprocess
from luma.core.render import canvas
from luma.core.interface.serial import bitbang



def makeint(i, base=10):
    try:
        return int(i, base=base)
    except:
        return 0
            
def get_gitver():
    major = 0
    minor = 0
    rev = 0
    gitrev = 0
    gitextra = 0
    dirty = 0

    def decode_version(v):
        version = v.split(".")
        major = 0
        minor = 0
        rev = 0
        if len(version) >= 3:
            rev = makeint(version[2])
        if len(version) >= 2:
            minor = makeint(version[1])
        if len(version) >= 1:
            major = makeint(version[0])
        return (major, minor, rev)
    git_rev_cmd = subprocess.Popen(["git", "describe", "--tags", "--long", "--dirty=+", "--abbrev=8"],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE)
    (git_stdout, _) = git_rev_cmd.communicate()
    if git_rev_cmd.wait() != 0:
        print('unable to get git version')
        return (major, minor, rev, gitrev, gitextra, dirty)
    raw_git_rev = git_stdout.decode().strip()

    if raw_git_rev[-1] == "+":
        raw_git_rev = raw_git_rev[:-1]
        dirty = 1

    parts = raw_git_rev.split("-")

    if len(parts) >= 3:
        if parts[0].startswith("v"):
            version = parts[0]
            if version.startswith("v"):
                version = parts[0][1:]
            (major, minor, rev) = decode_version(version)
        gitextra = makeint(parts[1])
        if parts[2].startswith("g"):
            gitrev = makeint(parts[2][1:], base=16)
    elif len(parts) >= 2:
        if parts[1].startswith("g"):
            gitrev = makeint(parts[1][1:], base=16)
        version = parts[0]
        if version.startswith("v"):
            version = parts[0][1:]
        (major, minor, rev) = decode_version(version)
    elif len(parts) >= 1:
        version = parts[0]
        if version.startswith("v"):
            version = parts[0][1:]
        (major, minor, rev) = decode_version(version)

    return (major, minor, rev, gitrev, gitextra, dirty)
        
def main():
    from luma.oled.device import ssd1322
    import luma.oled.device

    print("Initializing display")
    device = ssd1322(bitbang(SCLK=11, SDA=10, CE=7, DC=1, RST=12))
    with canvas(device) as draw:
        device.clear()
        (major, minor, rev, gitrev, gitextra, dirty) = get_gitver()
        if dirty == 1:
            dstring = "dirty"
        else:
            dstring = "clean"
        draw.text((0, 0), "Tester version {}.{}.{} {:x}+{} {}".format(major, minor, rev, gitrev, gitextra, dstring), fill="white")

    time.sleep(2)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
        
