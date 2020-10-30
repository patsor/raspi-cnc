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
        self.ax = cfg.axes["X"]
        self.ay = cfg.axes["X"]
        self.az = cfg.axes["X"]

        self.debug = debug

        self.mp = MotionPlanner(self.ax, self.ay, self.az,
                                self.sx, self.sy, self.sz)

        self.coordinates = self.load_coordinates()

    def load_coordinates(self):
        with open(cfg.coord_file) as file_obj:
            return json.load(file_obj)

    def save_coordinates(self):
        with open(cfg.coord_file, "w") as file_obj:
            json.dump(self.coordinates, file_obj, indent=4, sort_keys=True)

    def execute(self, gcode):
        # Get values from GCode
        f = gcode.get("F")
        g = gcode.get("G")
        r = gcode.get("R")
        x = gcode.get("X")
        y = gcode.get("Y")
        z = gcode.get("Z")

        # Calculate axis deltas
        dx = x - self.coordinates["X"] if x else 0
        dy = y - self.coordinates["Y"] if y else 0
        dz = z - self.coordinates["Z"] if z else 0

        # Init step intervals for X, Y and Z
        ix = iy = iz = []

        # Do action depending on GCode
        if g == "00":
            ix, iy, iz = self.mp.plan_move(dx, dy, dz)
        elif g == "01":
            feed_rate = f if f else self.ax["feed_rate"]

            if x and y and not z:
                ix, iy = self.mp.plan_interpolated_line(
                    dx, dy, feed_rate, "XY")
            elif x and not y and z:
                ix, iz = self.mp.plan_interpolated_line(
                    dx, dz, feed_rate, "XZ")
            elif not x and y and z:
                iy, iz = self.mp.plan_interpolated_line(
                    dy, dz, feed_rate, "YZ")
            else:
                print("Error in GCode! 3D linear interpolation not yet implemented")

        elif g == "02":
            feed_rate = f if f else self.ax["feed_rate"]

            if x and y and not z:
                ix, iy = self.mp.plan_interpolated_circle(
                    dx, dy, feed_rate, "XY")
            elif x and not y and z:
                ix, iz = self.mp.plan_interpolated_circle(
                    dx, dz, feed_rate, "XZ")
            elif not x and y and z:
                iy, iz = self.mp.plan_interpolated_circle(
                    dy, dz, feed_rate, "YZ")
            else:
                print("Error in GCode! 3D circular interpolation not yet implemented")

        elif g == "28":
            dx = self.ax["limits"][0] - self.coordinates["X"]
            dy = self.ay["limits"][0] - self.coordinates["Y"]
            dz = self.az["limits"][0] - self.coordinates["Z"]
            ix, iy, iz = self.mp.plan_move(dx, dy, dz)

        if not self.debug:
            p1 = Process(target=self.sx.step, args=(ix,))
            p2 = Process(target=self.sy.step, args=(iy,))
            p3 = Process(target=self.sz.step, args=(iz,))

            p1.start()
            p2.start()
            p3.start()

            p1.join()
            p2.join()
            p3.join()
        self.coordinates["X"] += dx
        self.coordinates["Y"] += dy
        self.coordinates["Z"] += dz
        self.save_coordinates()
