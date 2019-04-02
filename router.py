#!/usr/bin/env python

from __future__ import print_function

import json
import logging
import logging.config
from argparse import ArgumentParser
from multiprocessing import Process

import RPi.GPIO as GPIO

from gpio_handler import GPIOHandler
from stepper import Stepper
from gcode_parser import GCodeParser

def move(motor, dist):
    motor.move(dist)

class Router(object):
    def __init__(self, cfg_file, debug=False):
        self.cfg_file = cfg_file
        with open("logging.json") as log_cfg:
            log_dict = json.load(log_cfg)
        logging.config.dictConfig(log_dict)
        self.logger = logging.getLogger("main")
        self.logger.info("Parsing Config File [{}]".format(cfg_file))
        with open(cfg_file) as main_cfg:
            self.cfg = json.load(main_cfg)
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
            axis_cfg = self.cfg["axes"][axis]
            self.gpios[axis] = axis_cfg['gpio']

            self.handler.set_output_pins(self.gpios[axis].values())
            self.handler.default_output_pins(self.gpios[axis].values())

            self.pos[axis] = axis_cfg['position']
            self.pol[axis] = axis_cfg['polarity']
        
            step_angle = axis_cfg['step_angle']
            travel_per_rev = axis_cfg['travel_per_rev']
            microsteps = axis_cfg['microsteps']
            accel_rate = axis_cfg['acceleration_rate']
            v_max = axis_cfg['max_velocity']
            feed_rate = axis_cfg['max_feed_rate']

            self.lim[axis] = axis_cfg['limits']
            
            s = Stepper(
                "Stepper {} axis".format(axis),
                step_angle,
                travel_per_rev,
                microsteps,
                "traverse",
                "CW",
                self.gpios[axis],
                accel_rate,
                v_max,
                feed_rate,
                self.debug
            )
            self.motors[axis] = s
        
    def save_positions(self):
        for axis in self.axes:
            self.cfg["axes"][axis]["position"] = self.pos[axis]
        with open(self.cfg_file, "w") as file_obj:
            json.dump(self.cfg, file_obj, indent=4, sort_keys=True)
        
    def route(self, gcode_file):
        gcode = GCodeParser(gcode_file, self.lim)
        for command in gcode.instructions:
            self.logger.info(command)
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
            self.logger.debug("Calculating motion vector")
#            print("(x)   (dx) = ({:>6.2f})   ({:>7.2f})   ({:>6.2f})".format(self.pos["X"], delta["X"], target["X"]))
#            print("(y) + (dy) = ({:>6.2f}) + ({:>7.2f}) = ({:>6.2f})".format(self.pos["Y"], delta["Y"], target["Y"]))
#            print("(z)   (dz) = ({:>6.2f})   ({:>7.2f})   ({:>6.2f})".format(self.pos["Z"], delta["Z"], target["Z"]))
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
            self.handler.default_output_pins(self.gpios[axis].values())
        self.handler.cleanup()
        


def main():
    parser = ArgumentParser(description='Process materials')
    parser.add_argument('-i', '--gcode', dest='gcode', help='input g-code file', required=True)
    parser.add_argument('-d', '--debug', dest='debug', action='store_true', help='Set debug mode')
    args = parser.parse_args()
#    debug = args.debug
    instruction_file = args.gcode
    # GPIOs: [DIR,STP,M0,M1,M2]
#    cfg = Config("settings.cfg")
    cfg_file = "config.json"

    router = Router(cfg_file, args.debug)
    router.route(instruction_file)
    router.save_positions()


if __name__ == '__main__':
    main()
