#!/usr/bin/env python

from __future__ import print_function
import time

import RPi.GPIO as GPIO


def busy_wait(dt):
    current_time = time.time()
    while (time.time() < current_time + dt):
        pass

class Stepper(object):
    def __init__(self, name, mode, direction, gpios, debug=False):
        self.name = name
        self.mode = mode
        self.direction = direction
        self.gpios = gpios
        self.debug = debug
        self.modes = {
            1:[0, 0, 0],
            2:[0, 0, 1],
            4:[0, 1, 0],
            8:[0, 1, 1],
            16:[1, 0, 0],
            32:[1, 1, 1]
        }


    def get_mode(self):
        """Get mode of stepper motor"""
        return self.mode

    def set_mode(self, mode):
        """Set mode of stepper motor"""
        # Do not change mode if input mode equals current mode
#        if self.mode == mode:
#            return
        if mode not in self.modes:
            raise ValueError("Mode not available: {}".format(mode))
        bits = self.modes[self.mode]
        print("{} - Setting Microstepping Mode: 1/{} {}".format(self.name, mode, bits))

        if not self.debug:
            for i in range(3):
                GPIO.output(self.gpios[i+2], bits[0])
                time.sleep(0.1)
        self.mode = mode

    def get_direction(self):
        """Get direction of stepper motor"""
        return self.direction
        
    def set_direction(self, direction):
        """Set direction of stepper motor"""
        # Do not change direction if input direction equals current direction
#        if self.direction == direction:
#            return
        dir_str = ""
        if direction:
            dir_str = "CCW"
        else:
            dir_str = "CW"
        print("{} - Setting direction: {}".format(self.name, dir_str))
        if not self.debug:
            GPIO.output(self.gpios[0], direction)
#            GPIO.output(self.gpios[0], False)
            time.sleep(0.1)
        self.direction = direction

    def step(self, on_time, off_time):
        GPIO.output(self.gpios[1], True)
        busy_wait(on_time)
        GPIO.output(self.gpios[1], False)
        busy_wait(off_time)
