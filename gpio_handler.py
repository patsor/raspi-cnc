#!/usr/bin/env python

from __future__ import print_function

import logging

import RPi.GPIO as GPIO

class GPIOHandler(object):
    def __init__(self, mode=GPIO.BOARD, warnings=False, debug=False):
        self.debug = debug
        self.logger = logging.getLogger("GPIOHandler")
        self.set_mode(mode)
        self.set_warnings(warnings)

    def set_mode(self, mode):
        if mode:
            self.logger.debug("Setting GPIO Mode: BOARD")
        else:
            self.logger.debug("Setting GPIO Mode: BCM")
        if not self.debug:
            GPIO.setmode(mode)

    def set_warnings(self,warnings):
        if warnings:
            self.logger.debug("Activate GPIO Warnings")
        else:
            self.logger.debug("Deactivate GPIO Warnings")
        if not self.debug:
            GPIO.setwarnings(False)

    def set_output_pins(self, gpios):
        self.logger.debug("Setting GPIO output pins: {}".format(sorted(gpios)))
        if not self.debug:
            GPIO.setup(gpios, GPIO.OUT)

    def set_input_pins(self, gpios):
        self.logger.debug("Setting GPIO input pins: {}".format(gpios))
        if not self.debug:
            GPIO.setup(gpios, GPIO.IN)

    def default_output_pins(self, gpios):
        self.logger.debug("Defaulting GPIO output pins: {}".format(sorted(gpios)))
        if not self.debug:
            GPIO.output(gpios, False)

    def cleanup(self):
        self.logger.debug("Cleaning up GPIOs")
        if not self.debug:
            GPIO.cleanup()


def main():
    handler = GPIOHandler()

if __name__ == '__main__':
    main()
