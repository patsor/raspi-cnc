#!/usr/bin/env python

from argparse import ArgumentParser
import logging
import math
import sys
import threading
import time

# Uncomment for testing
# import RPi.GPIO as GPIO

import config as cfg


def _busy_wait(dt):
    """Implementation of busy wait for time critical step intervals."""
    current_time = time.time()
    while (time.time() < current_time+dt):
        pass


class Stepper(object):
    """
    A class for stepper motor methods.
    """

    def __init__(self, name, debug=False):
        stepper_cfg = cfg.steppers[name]
        self._name = name
        self._driver = stepper_cfg["driver"]
        self._mode = stepper_cfg["mode"]
        self._direction = stepper_cfg["direction"]
        self._step_angle = stepper_cfg["step_angle"]
        self._gpios = stepper_cfg["gpios"]

        axis_cfg = cfg.axes[name]
        self._lead = axis_cfg["lead"]
        self._ramp_type = axis_cfg["ramp_type"]
        self._accel = axis_cfg["accel"]

        self._logger = logging.getLogger(self.name)
        self._debug = debug

        if self._driver in cfg.drivers:
            self._modes = cfg.drivers[self._driver]["modes"]
        else:
            print("Error: Could not load config for {}".format(self._driver))
            sys.exit(1)

        self._dirs = {
            "CW": False,
            "CCW": True
        }

        if not self._debug:
            self._configure()

    def _configure(self):
        """Confgures motor for movement."""
        GPIO.setmode(GPIO.BOARD)
        GPIO.setwarnings(False)
        GPIO.setup(list(self._gpios.values()), GPIO.OUT)
        GPIO.output(list(self._gpios.values()), False)
        self.set_mode(self._mode, initial=True)
        self.set_direction(self._direction, initial=True)

    def enable(self):
        """Activate sleep mode"""
        if not self._debug:
            GPIO.output(self._gpios["sleep"], True)
            time.sleep(0.1)

    def disable(self):
        """Activate sleep mode"""
        if not self._debug:
            GPIO.output(self._gpios["sleep"], False)
            time.sleep(0.1)

    def get_mode(self):
        """Get mode of stepper motor."""
        return self._mode

    def set_mode(self, mode, initial=False):
        """Set mode of stepper motor."""
        # Do not change mode if input mode equals current mode
        if self._mode == mode and not initial:
            return
        if mode not in self._modes:
            raise ValueError("Mode not available: {}".format(mode))
        bits = self._modes[mode]
        self._logger.debug(
            "{} - Setting Microstepping Mode: 1/{} {}".format(self._name, mode, bits))

        if not self._debug:
            GPIO.output((self._gpios["m2"], self._gpios["m1"],
                         self._gpios["m0"]), (bits[0], bits[1], bits[2]))
            time.sleep(0.001)

        self.mode = mode

    def get_direction(self):
        """Get direction of stepper motor"""
        return self._direction

    def set_direction(self, direction, initial=False):
        """Set direction of stepper motor"""
        # Do not change direction if input direction equals current direction
        if self._direction == direction and not initial:
            return
        self._logger.debug(
            "{} - Setting direction: {}".format(self._name, direction))
        if not self._debug:
            GPIO.output(self._gpios["dir"], self._dirs[direction])
            time.sleep(0.001)
        self._direction = direction

    def step(self, interval):
        """Performs motor movement based on interval."""
        gpio_step = self._gpios["step"]

        for i, dt in interval:
            if i == -1:
                self.set_direction("CCW")
            else:
                self.set_direction("CW")
            for ele in (True, False):
                if i:
                    GPIO.output(gpio_step, ele)
                _busy_wait(dt)


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
    GPIO.output(list(s.gpios.values()), False)
    GPIO.cleanup()


if __name__ == "__main__":
    main()
