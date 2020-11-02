#!/usr/bin/env python

from argparse import ArgumentParser
import json
import logging
import logging.config

from stepper import Stepper
from machine import Machine
from gcode_parser import GCodeParser

import config as cfg


class Router(object):
    def __init__(self, debug=False):
        with open("logging.json") as log_cfg:
            log_dict = json.load(log_cfg)
        logging.config.dictConfig(log_dict)
        self.logger = logging.getLogger("main")

        self.debug = debug

    def run(self, gcode_file):
        """Runs GCode from GCode file."""
        sx = Stepper("X", self.debug)
        sy = Stepper("Y", self.debug)
        sz = Stepper("Z", self.debug)
        sx.enable()
        sy.enable()
        sz.enable()

        gcodes = GCodeParser.read_lines(gcode_file)
        machine = Machine(sx, sy, sz, self.debug)
        for gcode in gcodes:
            self.logger.info("Executing '{}'".format(gcode))
            machine.execute(gcode)

        sx.disable()
        sy.disable()
        sz.disable()
        if not self.debug:
            import RPi.GPIO as GPIO
            GPIO.cleanup()


def main():
    parser = ArgumentParser(description="Process materials")
    parser.add_argument("-i", "--gcode", dest="gcode",
                        help="input g-code file", required=True)
    parser.add_argument("-d", "--debug", dest="debug",
                        action="store_true", help="Set debug mode")
    args = parser.parse_args()

    router = Router(args.debug)

    router.run(args.gcode)


if __name__ == "__main__":
    main()
