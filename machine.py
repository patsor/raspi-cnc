#!/usr/bin/env python

import json
from multiprocessing import Process

import config as cfg
from stepper import Stepper
from motion_planner import MotionPlanner


class Machine(object):
    def __init__(self, sx, sy, sz, debug):
        self.sx = sx
        self.sy = sy
        self.sz = sz
        self.debug = debug

        self.mp = MotionPlanner()

        self.coordinates = self.load_coordinates()

    def load_coordinates(self):
        with open(cfg.coord_file) as file_obj:
            return json.load(file_obj)

    def save_coordinates(self):
        with open(cfg.coord_file, "w") as file_obj:
            json.dump(self.coordinates, file_obj, indent=4, sort_keys=True)

    def execute(self, gcode):
        g = gcode.get("G")
        x = gcode.get("X")
        y = gcode.get("Y")
        z = gcode.get("Z")
        r = gcode.get("R")
        delta_x = x - self.coordinates["X"] if x else 0
        delta_y = y - self.coordinates["Y"] if y else 0
        delta_z = z - self.coordinates["Z"] if z else 0
        steps_x = []
        steps_y = []
        steps_z = []
        if g == "00":
            steps_x, steps_y, steps_z = self.mp.plan_move(
                delta_x, delta_y, delta_z, self.sx, self.sy, self.sz)
        elif g == "01":
            steps_x, steps_y = self.mp.plan_interpolated_line(
                delta_x, delta_y, self.sx, self.sy)
        elif g == "02":
            steps_x, steps_y = self.mp.plan_interpolated_circle(
                r, self.sx, self.sy)
        elif g == "28":
            delta_x = cfg.steppers[self.sx.name]["limits"][0] - \
                self.coordinates["X"]
            delta_y = cfg.steppers[self.sy.name]["limits"][0] - \
                self.coordinates["Y"]
            delta_z = cfg.steppers[self.sz.name]["limits"][0] - \
                self.coordinates["Z"]
            steps_x, steps_y, steps_z = self.mp.plan_move(
                delta_x, delta_y, delta_z, self.sx, self.sy, self.sz)

        if not self.debug:
            p1 = Process(target=self.sx.step, args=(steps_x,))
            p2 = Process(target=self.sy.step, args=(steps_y,))
            p3 = Process(target=self.sz.step, args=(steps_z,))

            p1.start()
            p2.start()
            p3.start()

            p1.join()
            p2.join()
            p3.join()
        self.coordinates["X"] += delta_x
        self.coordinates["Y"] += delta_y
        self.coordinates["Z"] += delta_z
        print(self.coordinates)
        self.save_coordinates()
