#!/usr/bin/env python

from argparse import ArgumentParser
import logging
import sys
import threading
import time

import RPi.GPIO as GPIO

import config as cfg


class Stepper(object):
    def __init__(self, name, debug=False):
        stepper_cfg = cfg.steppers[name]
        self.name = name
        self.driver = stepper_cfg["driver"]
        self.mode = stepper_cfg["mode"]
        self.direction = stepper_cfg["direction"]
        self.step_angle = stepper_cfg["step_angle"]
        self.step_freq = stepper_cfg["step_freq"]
        self.gpios = stepper_cfg["gpios"]

        self.logger = logging.getLogger(self.name)
        self.debug = debug

        if self.driver in cfg.drivers:
            self.modes = cfg.drivers[self.driver]["modes"]
        else:
            print("Error: Could not load config for {}".format(self.driver))
            sys.exit(1)

        self.dirs = {
            "CW": False,
            "CCW": True
        }

        if not self.debug:
            self.init()

    def init(self):
        GPIO.setmode(GPIO.BOARD)
        GPIO.setwarnings(False)
        GPIO.setup(list(self.gpios.values()), GPIO.OUT)
        GPIO.output(list(self.gpios.values()), False)
        self.set_mode(self.mode, initial=True)
        self.set_direction(self.direction, initial=True)

    def enable(self):
        """Activate sleep mode"""
        if not self.debug:
            GPIO.output(self.gpios["sleep"], True)
            time.sleep(0.1)

    def disable(self):
        """Activate sleep mode"""
        if not self.debug:
            GPIO.output(self.gpios["sleep"], False)
            time.sleep(0.1)

    def get_mode(self):
        """Get mode of stepper motor"""
        return self.mode

    def set_mode(self, mode, initial=False):
        """Set mode of stepper motor"""
        # Do not change mode if input mode equals current mode
        if self.mode == mode and not initial:
            return
        if mode not in self.modes:
            raise ValueError("Mode not available: {}".format(mode))
        bits = self.modes[mode]
        self.logger.debug(
            "{} - Setting Microstepping Mode: 1/{} {}".format(self.name, mode, bits))

        if not self.debug:
            GPIO.output((self.gpios["m2"], self.gpios["m1"],
                         self.gpios["m0"]), (bits[0], bits[1], bits[2]))
            time.sleep(0.001)

        self.mode = mode

    def get_direction(self):
        """Get direction of stepper motor"""
        return self.direction

    def set_direction(self, direction, initial=False):
        """Set direction of stepper motor"""
        # Do not change direction if input direction equals current direction
        if self.direction == direction and not initial:
            return
        self.logger.debug(
            "{} - Setting direction: {}".format(self.name, direction))
        if not self.debug:
            GPIO.output(self.gpios["dir"], self.dirs[direction])
            time.sleep(0.001)
        self.direction = direction

    def get_step_frequency(self):
        return self.step_freq

    def set_step_frequency(self, freq):
        self.step_freq = freq

    def step(self, interval):
        gpio_step = self.gpios["step"]
        delay = 1.0 / (self.step_freq * 2)
        for i in interval:
            if i == -1:
                self.set_direction("CCW")
            else:
                self.set_direction("CW")
            for ele in (True, False):
                if i:
                    GPIO.output(gpio_step, ele)
                time.sleep(delay)


def main():
    parser = ArgumentParser(description="Invokes stepper motor movement")
    parser.add_argument("-n", "--name", dest="name",
                        help="Specify configuration for stepper motor based on config", default="default")
    parser.add_argument("-s", "--steps", dest="steps", type=int,
                        help="Specify number of steps for the motor to move", default=1)
    parser.add_argument("-m", "--mode", dest="mode",
                        type=int, help="Specify microstepping mode")
    parser.add_argument("-d", "--direction", dest="direction",
                        choices=["CW", "CCW"], help="Specify direction of movement")
    args = parser.parse_args()

    s = Stepper(
        args.name,
        debug=False
    )

    s.enable()

    if args.mode:
        s.set_mode(args.mode)

    if args.direction:
        s.set_direction(args.direction)

    interval = [
        1 if args.direction == "CW" else -1 for step in range(args.steps)
    ]

    s.step(interval)

    s.disable()
    GPIO.output(list(s["gpios"].values()), False)
    GPIO.cleanup()


if __name__ == "__main__":
    main()
