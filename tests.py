#!/usr/bin/env python

import os
import unittest

from gcode import GCode

from gcode_exceptions import DuplicateGCodeError
from gcode_exceptions import GCodeNotFoundError
from gcode_exceptions import GCodeOutOfBoundsError
from gcode_exceptions import InvalidGCodeError
from gcode_exceptions import MissingGCodeError
from gcode_exceptions import UnsupportedGCodeError

from gcode_parser import GCodeParser

from motion_planner import _mm_to_steps
from motion_planner import _mm_per_min_to_pps
from motion_planner import _plan_interpolated_arc
from motion_planner import _plan_interpolated_circle_bresenham
from motion_planner import _plan_interpolated_line_bresenham
from motion_planner import _plan_interpolated_line_constant
from motion_planner import _plan_move

from stepper import _configure_ramp_trapezoidal
from stepper import _configure_ramp_sigmoidal
from stepper import _add_ramp


class TestGCode(unittest.TestCase):
    def test_get(self):
        gcode = GCode({"G": "01", "X": "40"})
        self.assertEqual(gcode.get("G"), "01")
        self.assertEqual(gcode.get("X"), 40.0)
        self.assertEqual(gcode.get("Y"), None)


class TestGCodeParser(unittest.TestCase):

    def test_read_lines(self):
        filename = "test.csv"
        with open(filename, "w") as outf:
            outf.write("% Start program\nG01 X40.0 Y25.3\nG02 R15.5")

        g1 = GCode({"G": "01", "X": "40.0", "Y": "25.3"})
        g2 = GCode({"G": "02", "R": "15.5"})
        self.assertEqual(GCodeParser.read_lines(filename), [g1, g2])
        os.remove(filename)

    def test_parse_line(self):
        self.assertDictEqual(
            GCodeParser.parse_line("G01 X20 Y40 F60"),
            {"G": "01", "X": "20", "Y": "40", "F": "60"}
        )

        self.assertDictEqual(
            GCodeParser.parse_line("G02   R30  "),
            {"G": "02", "R": "30"}
        )

        self.assertDictEqual(
            GCodeParser.parse_line("   G02   R30  "),
            {"G": "02", "R": "30"}
        )

        self.assertIsNone(GCodeParser.parse_line(""), None)

        self.assertIsNone(GCodeParser.parse_line("%G01 X20 Y40 F60"), None)

        with self.assertRaises(MissingGCodeError):
            GCodeParser.parse_line("L01")

        with self.assertRaises(MissingGCodeError):
            GCodeParser.parse_line("X01")

        with self.assertRaises(InvalidGCodeError):
            GCodeParser.parse_line("XX")

        with self.assertRaises(DuplicateGCodeError):
            GCodeParser.parse_line("G01 M01 X10 Y10")

        with self.assertRaises(DuplicateGCodeError):
            GCodeParser.parse_line("G01 G01 X10 Y10")

        with self.assertRaises(UnsupportedGCodeError):
            GCodeParser.parse_line("G03")

        with self.assertRaises(InvalidGCodeError):
            GCodeParser.parse_line("G")

        with self.assertRaises(GCodeOutOfBoundsError):
            GCodeParser.parse_line("G00 X1000")

        with self.assertRaises(InvalidGCodeError):
            GCodeParser.parse_line("G02 X200")

        with self.assertRaises(InvalidGCodeError):
            GCodeParser.parse_line("G01 X20 Y20 Z20")

        with self.assertRaises(InvalidGCodeError):
            GCodeParser.parse_line("G28 X20 Y10")


class TestStepper(unittest.TestCase):

    def test_configure_ramp_trapezoidal(self):
        c = [0.01118, 0.004631]
        self.assertEqual([round(x, 6) for x in _configure_ramp_trapezoidal(
            200.0, 2, 1.8, 5, 200.0)], c)

        c = [0.015811, 0.006549, 0.005025, 0.004237]
        self.assertEqual([round(x, 6) for x in _configure_ramp_trapezoidal(
            200.0, 2, 1.8, 5, 100.0)], c)

        c = [
            0.022361,
            0.009262,
            0.007107,
            0.005992,
            0.005279,
            0.004772,
            0.004389,
            0.004085,
            0.003836
        ]
        self.assertEqual([round(x, 6) for x in _configure_ramp_trapezoidal(
            200.0, 2, 1.8, 5, 50.0)], c)

    def test_configure_ramp_sigmoidal(self):
        c = [0.005171, 0.004213, 0.003924, 0.003819, 0.003778]
        self.assertEqual([round(x, 6) for x in _configure_ramp_sigmoidal(
            200.0, 2, 1.8, 5, 200.0)], c)

        c = [
            0.013533,
            0.008808,
            0.006913,
            0.005905,
            0.005291,
            0.004886,
            0.004604,
            0.004402,
            0.004253,
            0.004141,
            0.004056,
            0.00399,
            0.003939,
            0.0039,
            0.003869,
            0.003844,
            0.003825,
            0.003809,
            0.003797,
            0.003788,
            0.00378,
            0.003774,
            0.003769
        ]
        self.assertEqual([round(x, 6) for x in _configure_ramp_sigmoidal(
            200.0, 2, 1.8, 5, 50.0)], c)

    def test_add_ramp(self):
        c = [0.015811, 0.006549, 0.005025, 0.004237]
        interval = [1, 1, 0, 0, 1, 1, 1, 0, 0, 0]
        result = [
            (1, 0.0079055),
            (1, 0.0032745),
            (0, 0.0025125),
            (0, 0.0021185),
            (1, 0.002),
            (1, 0.002),
            (1, 0.0021185),
            (0, 0.0025125),
            (0, 0.0032745),
            (0, 0.0079055)
        ]
        self.assertEqual(_add_ramp(interval, c, 0.004), result)

        c = [0.015811, 0.006549, 0.005025, 0.004237]
        interval = [1, 1, 0, 0, 1, 1]
        result = [
            (1, 0.0079055),
            (1, 0.0032745),
            (0, 0.0025125),
            (0, 0.0025125),
            (1, 0.0032745),
            (1, 0.0079055)
        ]
        self.assertEqual(_add_ramp(interval, c, 0.004), result)


class TestMotionPlanner(unittest.TestCase):

    def test_mm_to_steps(self):
        self.assertEqual(_mm_to_steps(100, 1.8, 1, 5), 4000)
        self.assertEqual(_mm_to_steps(5, 1.8, 2, 5), 400)
        self.assertEqual(_mm_to_steps(23, 1.8, 4, 5), 3680)
        self.assertEqual(_mm_to_steps(-40, 1.8, 1, 5), -1600)

    def test_mm_per_min_to_pps(self):
        self.assertEqual(_mm_per_min_to_pps(1200, 1.8, 1, 5), 800)
        self.assertEqual(_mm_per_min_to_pps(1200, 1.8, 2, 5), 1600)
        self.assertEqual(_mm_per_min_to_pps(600, 1.8, 4, 5), 1600)
        self.assertEqual(_mm_per_min_to_pps(600, 1.8, 8, 10), 1600)

    def test_move(self):
        x = [(1, 0.005)] * 8
        y = [(1, 0.01)] * 4
        z = [(1, 0.02)] * 3
        self.assertEqual(_plan_move(8, 4, 3, 200, 100, 50), (x, y, z))

        x = [(-1, 0.005)] * 8
        y = [(1, 0.01)] * 4
        z = [(-1, 0.02)] * 3
        self.assertEqual(_plan_move(-8, 4, -3, 200, 100, 50), (x, y, z))

    def test_interpolated_line_bresenham(self):
        x = [(1, 0.005)] * 8
        y = [
            (0, 0.01),
            (1, 0.01),
            (0, 0.01),
            (1, 0.01),
            (0, 0.01),
            (1, 0.01),
            (0, 0.01),
            (1, 0.01)
        ]
        self.assertEqual(_plan_interpolated_line_bresenham(
            8, 4, 200, 100), (x, y))

        x = [(1, 0.005)] * 8
        y = [
            (0, 0.01),
            (0, 0.01),
            (0, 0.01),
            (0, 0.01),
            (1, 0.01),
            (0, 0.01),
            (0, 0.01),
            (0, 0.01)
        ]
        self.assertEqual(_plan_interpolated_line_bresenham(
            8, 1, 200, 100), (x, y))

        x = [
            (0, 0.01),
            (0, 0.01),
            (0, 0.01),
            (0, 0.01),
            (1, 0.01),
            (0, 0.01),
            (0, 0.01),
            (0, 0.01)
        ]
        y = [(1, 0.005)] * 8
        self.assertEqual(_plan_interpolated_line_bresenham(
            1, 8, 100, 200), (x, y))

        x = [(-1, 0.005)] * 8
        y = [
            (0, 0.01),
            (1, 0.01),
            (0, 0.01),
            (1, 0.01),
            (0, 0.01),
            (1, 0.01),
            (0, 0.01),
            (1, 0.01)
        ]
        self.assertEqual(_plan_interpolated_line_bresenham(
            -8, 4, 200, 100), (x, y))

        x = [(x, 0.01) for x in [0, 0, 0, 0, -1, 0, 0, 0]]
        y = [(1, 0.005)] * 8
        self.assertEqual(_plan_interpolated_line_bresenham(
            -1, 8, 100, 200), (x, y))

        x = [(x, 0.01) for x in [0, 0, 0, 0, 1, 0, 0, 0]]
        y = [(-1, 0.005)] * 8
        self.assertEqual(_plan_interpolated_line_bresenham(
            1, -8, 100, 200), (x, y))

        x = [(x, 0.01) for x in [0, -1, 0, -1, 0, -1, 0, -1]]
        y = [(-1, 0.005)] * 8
        self.assertEqual(_plan_interpolated_line_bresenham(
            -4, -8, 100, 200), (x, y))

    def test_interpolated_line_constant(self):
        x = [(1, 0.005)] * 8
        y = [(1, 0.01)] * 4
        self.assertEqual(_plan_interpolated_line_constant(
            8, 4, 200, 100), (x, y))

        x = [(1, 0.005)] * 8
        y = [(1, 0.01)] * 1
        self.assertEqual(_plan_interpolated_line_constant(
            8, 1, 200, 100), (x, y))

        x = [(1, 0.01)] * 1
        y = [(1, 0.005)] * 8
        self.assertEqual(_plan_interpolated_line_constant(
            1, 8, 100, 200), (x, y))

        x = [(-1, 0.005)] * 8
        y = [(1, 0.01)] * 4
        self.assertEqual(_plan_interpolated_line_constant(
            -8, 4, 200, 100), (x, y))

        x = [(-1, 0.01)] * 1
        y = [(1, 0.005)] * 8
        self.assertEqual(_plan_interpolated_line_constant(
            -1, 8, 100, 200), (x, y))

    def test_interpolated_circle_bresenham(self):
        x = [
            0, 1, 1, 1, 1, 1, 1, 1,
            1, 1, 1, 0, 0, -1, -1, -1,
            -1, -1, -1, -1, -1, -1, -1, 0
        ]
        y = [
            1, 1, 1, 1, 1, 0, 0, -1,
            -1, -1, -1, -1, -1, -1, -1, -1,
            -1, 0, 0, 1, 1, 1, 1, 1
        ]
        self.assertEqual(_plan_interpolated_circle_bresenham(5), (x, y))

        x = [
            0, 0, 1, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1,
            1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 1, 0, 0,
            0, 0, -1, 0, -1, -1, -1, -1, -1, -1, -1, -1, -1,
            -1, -1, -1, -1, -1, -1, -1, -1, -1, 0, -1, 0, 0,
        ]
        y = [
            1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 1, 0, 0,
            0, 0, -1, 0, -1, -1, -1, -1, -1, -1, -1, -1, -1,
            -1, -1, -1, -1, -1, -1, -1, -1, -1, 0, -1, 0, 0,
            0, 0, 1, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1,
        ]
        self.assertEqual(_plan_interpolated_circle_bresenham(10), (x, y))

    def test_interpolated_arc_cw(self):
        x = [
            (1, 0.0451),
            (1, 0.0192),
            (1, 0.0152),
            (1, 0.0132),
            (1, 0.012),
            (1, 0.0112),
            (1, 0.0107),
            (1, 0.0103),
            (1, 0.0101),
            (1, 0.01),
            (1, 0.01),
            (1, 0.0101),
            (1, 0.0103),
            (1, 0.0107),
            (1, 0.0112),
            (1, 0.012),
            (1, 0.0132),
            (1, 0.0152),
            (1, 0.0192),
            (1, 0.0451),
            (-1, 0.0451),
            (-1, 0.0192),
            (-1, 0.0152),
            (-1, 0.0132),
            (-1, 0.012),
            (-1, 0.0112),
            (-1, 0.0107),
            (-1, 0.0103),
            (-1, 0.0101),
            (-1, 0.01),
            (-1, 0.01),
            (-1, 0.0101),
            (-1, 0.0103),
            (-1, 0.0107),
            (-1, 0.0112),
            (-1, 0.012),
            (-1, 0.0132),
            (-1, 0.0152),
            (-1, 0.0192),
            (-1, 0.0451)
        ]
        y = [
            (1, 0.01),
            (1, 0.0101),
            (1, 0.0103),
            (1, 0.0107),
            (1, 0.0112),
            (1, 0.012),
            (1, 0.0132),
            (1, 0.0152),
            (1, 0.0192),
            (1, 0.0451),
            (-1, 0.0451),
            (-1, 0.0192),
            (-1, 0.0152),
            (-1, 0.0132),
            (-1, 0.012),
            (-1, 0.0112),
            (-1, 0.0107),
            (-1, 0.0103),
            (-1, 0.0101),
            (-1, 0.01),
            (-1, 0.01),
            (-1, 0.0101),
            (-1, 0.0103),
            (-1, 0.0107),
            (-1, 0.0112),
            (-1, 0.012),
            (-1, 0.0132),
            (-1, 0.0152),
            (-1, 0.0192),
            (-1, 0.0451),
            (1, 0.0451),
            (1, 0.0192),
            (1, 0.0152),
            (1, 0.0132),
            (1, 0.012),
            (1, 0.0112),
            (1, 0.0107),
            (1, 0.0103),
            (1, 0.0101),
            (1, 0.01)
        ]

        ix, iy = _plan_interpolated_arc(10, 0, 0, 100.0, 100.0, True)
        for i in range(len(ix)):
            ix[i] = (ix[i][0], round(ix[i][1], 4))
            iy[i] = (iy[i][0], round(iy[i][1], 4))
        self.assertEqual(
            (ix, iy), (x, y))


if __name__ == "__main__":
    unittest.main()
