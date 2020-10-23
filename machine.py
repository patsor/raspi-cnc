#!/usr/bin/env python

import json
from multiprocessing import Process

import config as cfg
from stepper import Stepper
from motion_planner import MotionPlanner


def convert_mm_per_min_to_pps(value, lead, step_angle, mode):
    return value / lead / 60 * mode * (360 / step_angle)


class Machine(object):
    def __init__(self, sx, sy, sz, debug):
        self.sx = sx
        self.sy = sy
        self.sz = sz
        self.ax = cfg.axes["X"]
        self.ay = cfg.axes["X"]
        self.az = cfg.axes["X"]
        self.tfx, self.tfy, self.tfz = self.get_freqs((
            self.ax["traversal_rate"],
            self.ay["traversal_rate"],
            self.az["traversal_rate"]
        ))
        self.ffx, self.ffy, self.ffz = self.get_freqs((
            self.ax["feed_rate"],
            self.ay["feed_rate"],
            self.az["feed_rate"]
        ))

        self.debug = debug

        self.mp = MotionPlanner(self.ax, self.ay, self.az)

        self.coordinates = self.load_coordinates()

    def load_coordinates(self):
        with open(cfg.coord_file) as file_obj:
            return json.load(file_obj)

    def save_coordinates(self):
        with open(cfg.coord_file, "w") as file_obj:
            json.dump(self.coordinates, file_obj, indent=4, sort_keys=True)

    def get_freqs(self, values):
        fx = convert_mm_per_min_to_pps(
            values[0],
            self.ax["lead"],
            self.sx.step_angle,
            self.sx.mode
        )
        fy = convert_mm_per_min_to_pps(
            values[1],
            self.ay["lead"],
            self.sy.step_angle,
            self.sy.mode
        )
        fz = convert_mm_per_min_to_pps(
            values[2],
            self.az["lead"],
            self.sz.step_angle,
            self.sz.mode
        )
        return fx, fy, fz

    def execute(self, gcode):
        g = gcode.get("G")
        x = gcode.get("X")
        y = gcode.get("Y")
        z = gcode.get("Z")
        r = gcode.get("R")
        f = gcode.get("F")
        if f:
            self.ffx, self.ffy, self.ffz = self.get_freqs(
                (f, f, f))
        delta_x = x - self.coordinates["X"] if x else 0
        delta_y = y - self.coordinates["Y"] if y else 0
        delta_z = z - self.coordinates["Z"] if z else 0
        # feed_rate = f if gcode.get("F")
        steps_x = []
        steps_y = []
        steps_z = []
        if g == "00":
            self.sx.set_step_frequency(self.tfx)
            self.sy.set_step_frequency(self.tfy)
            self.sz.set_step_frequency(self.tfz)
            steps_x, steps_y, steps_z = self.mp.plan_move(
                delta_x, delta_y, delta_z, self.sx, self.sy, self.sz)
        elif g == "01":
            self.sx.set_step_frequency(self.ffx)
            self.sy.set_step_frequency(self.ffy)
            self.sz.set_step_frequency(self.ffz)
            steps_x, steps_y = self.mp.plan_interpolated_line(
                delta_x, delta_y, self.sx, self.sy)
        elif g == "02":
            self.sx.set_step_frequency(self.ffx)
            self.sy.set_step_frequency(self.ffy)
            self.sz.set_step_frequency(self.ffz)
            steps_x, steps_y = self.mp.plan_interpolated_circle(
                r, self.sx, self.sy)
        elif g == "28":
            self.sx.set_step_frequency(self.tfx)
            self.sy.set_step_frequency(self.tfy)
            self.sz.set_step_frequency(self.tfz)
            delta_x = cfg.axes["X"]["limits"][0] - \
                self.coordinates["X"]
            delta_y = cfg.axes["Y"]["limits"][0] - \
                self.coordinates["Y"]
            delta_z = cfg.axes["Z"]["limits"][0] - \
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
