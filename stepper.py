#!/usr/bin/env python

import json
import time
import logging

from argparse import ArgumentParser

import RPi.GPIO as GPIO


def busy_wait(dt):
    """Busy wait as sleep can vary"""
    current_time = time.time()
    while (time.time() < current_time + dt):
        pass

class Stepper(object):
    def __init__(self, name, driver, mode, direction, gpios, debug=False):
        self.name = name
        self.driver = driver
        self.mode = mode
        self.direction = direction
        self.gpios = gpios
        self.logger = logging.getLogger(self.name)
        self.debug = debug
        

        if self.driver == "DRV8825":
            # Microstepping modes of DRV8825
            # Microstepping mode 1/n: M2, M1, M0
            # Example: 1/2 (Half step): M2=0, M1=0, M0=1
            self.modes = {
                1: (0, 0, 0),
                2: (0, 0, 1),
                4: (0, 1, 0),
                8: (0, 1, 1),
                16: (1, 0, 0),
                32: (1, 1, 0)
            }
        elif self.driver == "TB67S249FTG":
            # Microstepping modes of TB67S249FTG
            # Microstepping mode 1/n: M2, M1, M0
            self.modes = {
                0: (0, 0, 0),
                1: (1, 0, 0),
                2: (0, 1, 0), # non-circular half step (100% current, high torque)
                # 2: (0, 0, 1), # circular half step (71% current, medium torque)
                4: (1, 1, 0),
                8: (1, 0, 1),
                16: (0, 1, 1),
                32: (1, 1, 1)
            }
        else:
            # defaulting to TB67S249FTG
            self.modes = {
                0: (0, 0, 0),
                1: (1, 0, 0),
                2: (0, 1, 0),
                4: (1, 1, 0),
                8: (1, 0, 1),
                16: (0, 1, 1),
                32: (1, 1, 1)
            }
            
        self.dirs = {
            "CW": False,
            "CCW": True
        }
        
        self.set_mode(mode, initial=True)
        self.set_direction(direction, initial=True)

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
        self.logger.debug("{} - Setting Microstepping Mode: 1/{} {}".format(self.name, mode, bits))

        if not self.debug:
            GPIO.output((self.gpios["m2"], self.gpios["m1"], self.gpios["m0"]), (bits[0], bits[1], bits[2]))
            time.sleep(0.1)
            
        self.mode = mode

    def get_direction(self):
        """Get direction of stepper motor"""
        return self.direction
        
    def set_direction(self, direction, initial=False):
        """Set direction of stepper motor"""
        # Do not change direction if input direction equals current direction
        if self.direction == direction and not initial:
            return
        self.logger.debug("{} - Setting direction: {}".format(self.name, direction))
        if not self.debug:
            GPIO.output(self.gpios["dir"], self.dirs[direction])
            time.sleep(0.1)
        self.direction = direction

    def step(self, delay):
        GPIO.output(self.gpios["step"], True)
        busy_wait(delay)
        GPIO.output(self.gpios["step"], False)
        busy_wait(delay)
        
def main():
    parser = ArgumentParser(description="Plans axis movements")
    parser.add_argument("-s", "--steps", dest="steps", type=int, help="Specify number of steps for the motor to move", required=True)
    parser.add_argument("-d", "--direction", dest="direction", choices=["CW", "CCW"], help="Specify direction of movement", default="CW")
    parser.add_argument("-a", "--axis", dest="axis", choices=["X", "Y", "Z"], help="Specify axis", required=True)
    parser.add_argument("-c", "--config", dest="config", help="Specify config")
    args = parser.parse_args()

    with open(args.config) as file_obj:
        cfg = json.load(file_obj)
        
    name = "Stepper - Test"
    driver = cfg["axes"][args.axis]["driver"]
    mode = 1
    direction = args.direction
    gpios = cfg["axes"][args.axis]["gpio"]
    debug=False

    if not debug:
        GPIO.setmode(GPIO.BOARD)
        GPIO.setwarnings(False)
        GPIO.setup(gpios.values(), GPIO.OUT)
        GPIO.output(gpios.values(), False)
        
        s = Stepper(
            name,
            driver,
            mode,
            direction,
            gpios,
            debug
        )

        for i in range(args.steps):
            s.step(0.0006)

        GPIO.output(gpios.values(), False)
        GPIO.cleanup()

if __name__ == "__main__":
    main()
