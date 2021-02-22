#!/usr/bin/env python

import json
from multiprocessing import Process

import config as cfg
from stepper import Stepper
from motion_planner import MotionPlanner


class Machine(object):
    """Machine class for GCode interpretation."""

    def __init__(self, sx, sy, sz, debug):
        self._sx = sx
        self._sy = sy
        self._sz = sz
        self._plane = "XY"

        self._debug = debug

        self.mp = MotionPlanner()

        self._coordinates = self._load_coordinates()

    def _load_coordinates(self):
        """Loads coordinates from JSON file."""
        with open(cfg.coord_file) as file_obj:
            return json.load(file_obj)

    def _save_coordinates(self):
        """Saves coordinates to JSON file."""
        with open(cfg.coord_file, "w") as file_obj:
            json.dump(self._coordinates, file_obj, indent=4, sort_keys=True)

    def execute(self, gcode):
        """Executes GCode.

        Parameters:
            gcode (GCode): GCode object
        """

        # Get gcode command
        g = gcode.get("G")

        # Init step intervals for X, Y and Z
        ix = []
        iy = []
        iz = []

        # Do action depending on GCode
        # Rapid positioning
        if g == "00":
            x = gcode.get("X")
            y = gcode.get("Y")
            z = gcode.get("Z")
            # Calculate axis deltas
            dx = x - self._coordinates["X"] if x else 0
            dy = y - self._coordinates["Y"] if y else 0
            dz = z - self._coordinates["Z"] if z else 0
            vx = cfg.AXIS_TRAVERSAL_MM_PER_MIN_X
            vy = cfg.AXIS_TRAVERSAL_MM_PER_MIN_Y
            vz = cfg.AXIS_TRAVERSAL_MM_PER_MIN_Z
            ds = (("x", dx), ("y", dy), ("z", dz))
            v = (("x", vx), ("y", vy), ("z", vz))
            ix, iy, iz = self.mp.plan_move(ds, v)

        # Linear interpolation
        elif g == "01":
            f = gcode.get("F")
            x = gcode.get("X")
            y = gcode.get("Y")
            z = gcode.get("Z")
            # Calculate axis deltas
            dx = x - self._coordinates["X"] if x else 0
            dy = y - self._coordinates["Y"] if y else 0
            dz = z - self._coordinates["Z"] if z else 0
            feed_rate = float(f) if f else cfg.AXIS_FEED_MM_PER_MIN_X

            if x and y and not z:
                delta = (("x", dx), ("y", dy))
                ix, iy = self.mp.plan_interpolated_line(delta, feed_rate)
            elif x and not y and z:
                delta = (("x", dx), ("z", dz))
                ix, iz = self.mp.plan_interpolated_line(delta, feed_rate)
            elif not x and y and z:
                delta = (("y", dy), ("z", dz))
                iy, iz = self.mp.plan_interpolated_line(delta, feed_rate)
            else:
                print("Error in GCode! 3D linear interpolation not yet implemented")

        # Circular interpolation
        elif g in ("02", "03"):
            f = gcode.get("F")
            i = gcode.get("I")
            j = gcode.get("J")
            k = gcode.get("K")
            r = gcode.get("R")
            x = gcode.get("X")
            y = gcode.get("Y")
            z = gcode.get("Z")
            # Calculate axis deltas
            dx = x - self._coordinates["X"] if x else 0
            dy = y - self._coordinates["Y"] if y else 0
            dz = z - self._coordinates["Z"] if z else 0

            cw = True if g == "02" else False
            feed_rate = float(f) if f else cfg.AXIS_FEED_MM_PER_MIN_X
            if self._plane == "XY":
                xs = -i if i else 0
                ys = -j if j else 0
                if not r:
                    r = math.sqrt(xs*xs + ys*ys)
                ds = (("x", xs), ("y", ys))
                de = (("x", dx), ("y", dy))
                ix, iy = self.mp.plan_interpolated_arc(
                    r, ds, de, feed_rate, cw
                )
            elif self._plane == "XZ":
                if i and k and not r:
                    r = math.sqrt(i*i + k*k)
                    x_start = -i
                    z_start = -k
                ix, iz = self.mp.plan_interpolated_arc(
                    r, x_start, z_start, dx, dz, feed_rate, cw
                )
            elif self._plane == "YZ":
                if j and k and not r:
                    r = math.sqrt(j*j + k*k)
                    y_start = -j
                    z_start = -k
                iy, iz = self.mp.plan_interpolated_arc(
                    r, y_start, z_start, dy, dz, feed_rate, cw
                )
            else:
                print("Error in GCode! 3D circular interpolation not yet implemented")

        # XY plane selection
        elif g == "17":
            self._plane = "XY"

        # XZ plane selection
        elif g == "18":
            self._plane = "XZ"

        # YZ plane selection
        elif g == "19":
            self._plane = "YZ"

        # Homing
        elif g == "28":
            # Calculate new deltas based on axis limits
            dx = cfg.AXIS_LIMITS_X[0] - self._coordinates["X"]
            dy = cfg.AXIS_LIMITS_Y[0] - self._coordinates["Y"]
            dz = cfg.AXIS_LIMITS_Z[0] - self._coordinates["Z"]
            vx = cfg.AXIS_TRAVERSAL_MM_PER_MIN_X
            vy = cfg.AXIS_TRAVERSAL_MM_PER_MIN_Y
            vz = cfg.AXIS_TRAVERSAL_MM_PER_MIN_Z
            ds = (("x", dx), ("y", dy), ("z", dz))
            v = (("x", vx), ("y", vy), ("z", vz))
            ix, iy, iz = self.mp.plan_move(ds, v)

        if not self._debug:
            # Creating a process for each motor handling step intervals
            p1 = Process(target=self._sx.step, args=(ix,))
            p2 = Process(target=self._sy.step, args=(iy,))
            p3 = Process(target=self._sz.step, args=(iz,))

            # Starting the processes
            p1.start()
            p2.start()
            p3.start()

            # Joining the processes
            p1.join()
            p2.join()
            p3.join()

        # Update the coordinates
        self._coordinates["X"] += dx
        self._coordinates["Y"] += dy
        self._coordinates["Z"] += dz
        self._save_coordinates()
