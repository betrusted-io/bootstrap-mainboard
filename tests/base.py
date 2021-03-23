import time
from luma.core.render import canvas

class Test:
    def __init__(self, name="Unimplemented", shortname=None):
        self.passing = False
        self.has_run = False
        self.name = name
        self.shortlen = 6
        if shortname == None:
            self.shortname = name[:self.shortlen]
        else:
            self.shortname = shortname[:self.shortlen]

    def short_status(self):
        if self.has_run == False:
            return self.shortname.ljust(self.shortlen) + ' --'
        if self.has_run and self.passing:
            return self.shortname.ljust(self.shortlen) + ' OK'
        else:
            return self.shortname.ljust(self.shortlen) + ' NG'

    def is_passing(self):
        return self.passing

    def has_run(self):
        return self.has_run

    def reset(self):
        self.passing = False
        self.has_run = False

    def run(self, oled):
        with canvas(oled) as draw:
            oled.clear()
            draw.text((0,0), "Test '{}' not implemented!".format(self.name))

        time.sleep(1)
        self.has_run = True
        self.passing = False

        return self.passing
