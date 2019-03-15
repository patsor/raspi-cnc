#!/usr/bin/env python

from __future__ import print_function

import RPi.GPIO as GPIO

class GPIOHandler(object):
    def __init__(self, mode=GPIO.BOARD, warnings=False, debug=False):
        self.debug = debug
        self.set_mode(mode)
        self.set_warnings(warnings)

    def set_mode(self, mode):
        if mode:
            print("Setting GPIO Mode: BOARD")
        else:
            print("Setting GPIO Mode: BCM")
        if not self.debug:
            GPIO.setmode(mode)

    def set_warnings(self,warnings):
        if warnings:
            print("Activate GPIO Warnings")
        else:
            print("Deactivate GPIO Warnings")
        if not self.debug:
            GPIO.setwarnings(False)

    def set_output_pins(self, gpios):
        print("Setting GPIO output pins: {}".format(sorted(gpios)))
        if not self.debug:
            for gpio in gpios:
                GPIO.setup(gpio, GPIO.OUT)

    def set_input_pins(self,gpios):
        print("Setting GPIO input pins: {}".format(gpios))
        if not self.debug:
            for gpio in gpios:
                GPIO.setup(gpio, GPIO.IN)

    def default_output_pins(self,gpios):
        print("Defaulting GPIO output pins: {}".format(sorted(gpios)))
        if not self.debug:
            for gpio in gpios:
                GPIO.output(gpio, False)

    def cleanup(self):
        print("Cleaning up GPIOs")
        if not self.debug:
            GPIO.cleanup()


def main():
    handler = GPIOHandler()

if __name__ == '__main__':
    main()
