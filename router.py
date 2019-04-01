#!/usr/bin/env python

from __future__ import print_function

import sys
import time
from argparse import ArgumentParser
import ConfigParser
from multiprocessing import Process

import RPi.GPIO as GPIO

from nicelog import nprint, nflush
from gpio_handler import GPIOHandler
from stepper import Stepper
from instruction_set import InstructionSet

def move(motor, dist):
    motor.move(dist)

class Router(object):
    def __init__(self, cfg_file, debug=False):
        self.cfg_file = cfg_file
        self.cfg = ConfigParser.ConfigParser()
        self.cfg.read(cfg_file)
        self.debug = debug
        self.axes = ["X", "Y", "Z"]
        self.handler = GPIOHandler(GPIO.BOARD, False, debug)
        self.configure_motors()

    def configure_motors(self):
        self.gpios = {}
        self.pos = {}
        self.pol = {}
        self.lim = {}
        self.motors = {}
        for axis in self.axes:
            self.gpios[axis] = [int(x) for x in self.cfg.get(axis, 'gpio_pins').split(",")]

            self.handler.set_output_pins(self.gpios[axis])
            self.handler.default_output_pins(self.gpios[axis])

            self.pos[axis] = self.cfg.getfloat(axis, 'position')
            self.pol[axis] = self.cfg.getint(axis, 'polarity')
        
            sa = self.cfg.getfloat(axis, 'step_angle')
            tpr = self.cfg.getfloat(axis, 'travel_per_rev')
            mi = self.cfg.getint(axis, 'microstepping_mode')
            a = self.cfg.getfloat(axis, 'acceleration_rate')
            v = self.cfg.getfloat(axis, 'max_velocity')
            f = self.cfg.getfloat(axis, 'max_feed_rate')

            self.lim[axis] = (
                self.cfg.getfloat(axis, 'min_travel'),
                self.cfg.getfloat(axis, 'max_travel')
            )

            s = Stepper(
                "Stepper {} axis".format(axis),
                sa,
                tpr,
                mi,
                "traverse",
                "CW",
                self.gpios[axis],
                a,
                v,
                f,
                self.debug
            )
            self.motors[axis] = s
        
    def save_positions(self):
        for axis in self.axes:
            self.cfg.set(axis, 'position', self.pos[axis])
        with open(self.cfg_file, "wb") as configfile:
            self.cfg.write(configfile)
        
    def route(self, instruction_file):
        inst_set = InstructionSet(instruction_file, self.lim)
        for command in inst_set.instructions:
#            print(command)
            # vectors for axis movement
            delta = {}
            for axis in self.axes:
                delta[axis] = 0.0
            for (prefix, val) in command:
                if prefix == "G":
                    if val == "00":
                        for axis in self.axes:
                            self.motors[axis].set_motion_type("traverse")
                    else:
                        for axis in self.axes:
                            self.motors[axis].set_motion_type("feed")
                elif prefix == "X":
                    delta[prefix] = float(val) - self.pos[prefix]
                elif prefix == "Y":
                    delta[prefix] = float(val) - self.pos[prefix]
                elif prefix == "Z":
                    delta[prefix] = float(val) - self.pos[prefix]
            text="Calculating motion vector"
            nprint(text)
#            print("(x)   (dx) = ({:>6.2f})   ({:>7.2f})   ({:>6.2f})".format(self.pos["X"], delta["X"], target["X"]))
#            print("(y) + (dy) = ({:>6.2f}) + ({:>7.2f}) = ({:>6.2f})".format(self.pos["Y"], delta["Y"], target["Y"]))
#            print("(z)   (dz) = ({:>6.2f})   ({:>7.2f})   ({:>6.2f})".format(self.pos["Z"], delta["Z"], target["Z"]))
            nflush(text)
            # Starting axis movement as parallel processes
            procs = []
            for axis in self.axes:
                if delta[axis] < 0:
                    if self.pol[axis]:
                        self.motors[axis].set_direction("CW")
                    else:
                        self.motors[axis].set_direction("CCW")
                elif delta[axis] > 0:
                    if self.pol[axis]:
                        self.motors[axis].set_direction("CCW")
                    else:
                        self.motors[axis].set_direction("CW")
                else:
                    continue
                proc = Process(target=move, args=(self.motors[axis], delta[axis]))
                procs.append(proc)

            for proc in procs:
                proc.start()

            for proc in procs:
                proc.join()

            for axis in self.axes:
                self.pos[axis] += delta[axis]

        for axis in self.axes:
            self.handler.default_output_pins(self.gpios[axis])
        self.handler.cleanup()
        


def main():
    parser = ArgumentParser(description='Process materials')
    parser.add_argument('-i', '--input', dest='input', help='input g-code file', required=True)
    parser.add_argument('-d', '--debug', dest='debug', action='store_true', help='Set debug mode')
    args = parser.parse_args()
#    debug = args.debug
    instruction_file = args.input
    # GPIOs: [DIR,STP,M0,M1,M2]
#    cfg = Config("settings.cfg")
    cfg_file = "settings.cfg"

    router = Router(cfg_file, args.debug)
    router.route(instruction_file)
    router.save_positions()


if __name__ == '__main__':
    main()
