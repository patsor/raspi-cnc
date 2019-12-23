#!/usr/bin/env python

from __future__ import print_function

import json
import logging
import logging.config
from argparse import ArgumentParser
from multiprocessing import Process

from gpio_handler import GPIOHandler
from stepper import Stepper
from motion_planner import MotionPlanner
from gcode_parser import GCodeParser
from db_conn import DBConnection

def move(motor, motion_planner, dist, debug):
    step_intervals = motion_planner.plan_line(dist)
    for step_interval in step_intervals:
        if not debug:
            motor.step(step_interval)

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

        db_host = self.cfg["general"]["db_host"]
        db_port = self.cfg["general"]["db_port"]
        db_name = self.cfg["general"]["db_name"]
        
        self.db = DBConnection(db_host, db_port, db_name)
        
        self.coord_file = "coord.json"
        self.coordinates = self.load_coordinates(self.coord_file)
        self.debug = debug

        self.axes = ["X", "Y", "Z"]
        self.handler = GPIOHandler(GPIO.BOARD, False, debug)
        self.configure_motors()

    def configure_motors(self):
        self.gpios = {}
        self.pol = {}
        self.lim = {}
        self.motion_planner = {}
        self.motors = {}

        for axis in self.axes:
            axis_cfg = self.cfg["axes"][axis]
            self.gpios[axis] = axis_cfg['gpio']

            self.handler.set_output_pins(self.gpios[axis].values())
            self.handler.default_output_pins(self.gpios[axis].values())

#            self.pos[axis] = axis_cfg['position']
            self.pol[axis] = axis_cfg['polarity']

            ramp_type = axis_cfg['ramp_type']
            step_angle = axis_cfg['step_angle']
            travel_per_rev = axis_cfg['travel_per_rev']
            microsteps = axis_cfg['microsteps']
            accel_rate = axis_cfg['acceleration_rate']
            v_max = axis_cfg['max_velocity']
            feed_rate = axis_cfg['max_feed_rate']

            self.lim[axis] = axis_cfg['limits']
            
            s = Stepper(
                "Stepper {} axis".format(axis),
                microsteps,
                "CW",
                self.gpios[axis],
                self.debug
            )
            mp = MotionPlanner(
                "{} axis".format(axis),
                "traverse",
                ramp_type,
                step_angle,
                travel_per_rev,
                microsteps,
                accel_rate,
                v_max,
                feed_rate,
                self.db,
                self.debug
            )
            self.motors[axis] = s
            self.motion_planner[axis] = mp

    def load_coordinates(self, coord_file):
        with open(coord_file) as coord:
            return json.load(coord)
            
    def save_coordinates(self):
#        for axis in self.axes:
#            self.cfg[axis]["position"] = self.coordinates[axis]
        with open(self.coord_file, "w") as file_obj:
            json.dump(self.coordinates, file_obj, indent=4, sort_keys=True)
        
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
                            self.motion_planner[axis].set_motion_type("traverse")
                    elif val == "01":
                        for axis in self.axes:
                            self.motion_planner[axis].set_motion_type("feed")
                    elif val == "28":
                        for axis in self.axes:
                            self.motion_planner[axis].set_motion_type("traverse")
                            delta[axis] = - self.coordinates[axis]
                elif prefix == "X":
                    delta[prefix] = float(val) - self.coordinates[prefix]
                elif prefix == "Y":
                    delta[prefix] = float(val) - self.coordinates[prefix]
                elif prefix == "Z":
                    delta[prefix] = float(val) - self.coordinates[prefix]
            self.logger.debug("Calculating motion vector")
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
                proc = Process(target=move, args=(self.motors[axis], self.motion_planner[axis], delta[axis], self.debug))
                procs.append(proc)

            for proc in procs:
                proc.start()

            for proc in procs:
                proc.join()

            for axis in self.axes:
                self.coordinates[axis] += delta[axis]

        for axis in self.axes:
            self.handler.default_output_pins(self.gpios[axis].values())
        self.handler.cleanup()
        


def main():
    parser = ArgumentParser(description='Process materials')
    parser.add_argument('-i', '--gcode', dest='gcode', help='input g-code file', required=True)
    parser.add_argument('-d', '--debug', dest='debug', action='store_true', help='Set debug mode')
    args = parser.parse_args()
    # GPIOs: [DIR,STP,M0,M1,M2]
#    cfg = Config("settings.cfg")
    cfg_file = "config.json"

    router = Router(cfg_file, args.debug)
    router.route(args.gcode)
    router.save_coordinates()


if __name__ == '__main__':
    main()
