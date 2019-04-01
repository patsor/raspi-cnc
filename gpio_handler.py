#!/usr/bin/env python

from __future__ import print_function

from nicelog import nprint, nflush

import RPi.GPIO as GPIO

class GPIOHandler(object):
    def __init__(self, mode=GPIO.BOARD, warnings=False, debug=False):
        self.debug = debug
        self.set_mode(mode)
        self.set_warnings(warnings)

    def set_mode(self, mode):
        text=""
        if mode:
            text="Setting GPIO Mode: BOARD"
            nprint(text, "info")
        else:
            text="Setting GPIO Mode: BCM"
            nprint(text, "info")
        if not self.debug:
            GPIO.setmode(mode)
        nflush(text, "info")

    def set_warnings(self,warnings):
        text=""
        if warnings:
            text="Activate GPIO Warnings"
            nprint(text, "info")
        else:
            text="Deactivate GPIO Warnings"
            nprint(text, "info")
        if not self.debug:
            GPIO.setwarnings(False)
        nflush(text, "info")

    def set_output_pins(self, gpios):
        text="Setting GPIO output pins: {}".format(sorted(gpios))
        nprint(text)
        if not self.debug:
            for gpio in gpios:
                GPIO.setup(gpio, GPIO.OUT)
        nflush(text)

    def set_input_pins(self, gpios):
        text="Setting GPIO input pins: {}".format(gpios)
        nprint(text)
        if not self.debug:
            for gpio in gpios:
                GPIO.setup(gpio, GPIO.IN)
        nflush(text)

    def default_output_pins(self,gpios):
        text="Defaulting GPIO output pins: {}".format(sorted(gpios))
        nprint(text)
        if not self.debug:
            for gpio in gpios:
                GPIO.output(gpio, False)
        nflush(text)

    def cleanup(self):
        text="Cleaning up GPIOs"
        nprint(text)
        if not self.debug:
            GPIO.cleanup()
        nflush(text)


def main():
    handler = GPIOHandler()

if __name__ == '__main__':
    main()
