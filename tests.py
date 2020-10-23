#!/usr/bin/env python

import os
import unittest

from motion_planner import _calc_steps, _plan_move, _plan_interpolated_line, _plan_interpolated_circle

from gcode_exceptions import DuplicateGCodeError, GCodeNotFoundError, InvalidGCodeError, MissingGCodeError, UnsupportedGCodeError, GCodeOutOfBoundsError

from gcode_parser import GCodeParser
from gcode import GCode


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


class TestMotionPlanner(unittest.TestCase):

    def test_calc_steps(self):
        self.assertEqual(_calc_steps(100, 1.8, 1, 5), 4000)
        self.assertEqual(_calc_steps(5, 1.8, 2, 5), 400)
        self.assertEqual(_calc_steps(23, 1.8, 4, 5), 3680)
        self.assertEqual(_calc_steps(-40, 1.8, 1, 5), 1600)

    def test_move(self):
        x = [1, 1, 1, 1, 1, 1, 1, 1]
        y = [1, 1, 1, 1, 0, 0, 0, 0]
        z = [1, 1, 1, 0, 0, 0, 0, 0]
        self.assertEqual(_plan_move(8, 4, 3), (x, y, z))

        x = [-1, -1, -1, -1, -1, -1, -1, -1]
        y = [1, 1, 1, 1, 0, 0, 0, 0]
        z = [-1, -1, -1, 0, 0, 0, 0, 0]
        self.assertEqual(_plan_move(-8, 4, -3), (x, y, z))

    def test_interpolated_line(self):
        x = [1, 0, 1, 1, 0, 1, 1, 0, 1, 1, 0, 1]
        y = [0, 1, 0, 0, 1, 0, 0, 1, 0, 0, 1, 0]
        self.assertEqual(_plan_interpolated_line(8, 4), (x, y))

        x = [1, 1, 1, 1, 1, 1, 1, 0, 1]
        y = [0, 0, 0, 0, 0, 0, 0, 1, 0]
        self.assertEqual(_plan_interpolated_line(8, 1), (x, y))

        x = [0, 0, 0, 0, 0, 0, 0, 0, 1]
        y = [1, 1, 1, 1, 1, 1, 1, 1, 0]
        self.assertEqual(_plan_interpolated_line(1, 8), (x, y))

        x = [-1, 0, -1, -1, 0, -1, -1, 0, -1, -1, 0, -1]
        y = [0, 1, 0, 0, 1, 0, 0, 1, 0, 0, 1, 0]
        self.assertEqual(_plan_interpolated_line(-8, 4), (x, y))

        x = [0, 0, 0, 0, 0, 0, 0, 0, -1]
        y = [1, 1, 1, 1, 1, 1, 1, 1, 0]
        self.assertEqual(_plan_interpolated_line(-1, 8), (x, y))

        x = [0, 0, -1, 0, 0, -1, 0, 0, -1, 0, 0, -1]
        y = [-1, -1, 0, -1, -1, 0, -1, -1, 0, -1, -1, 0]
        self.assertEqual(_plan_interpolated_line(-4, -8), (x, y))

    def test_interpolated_circle(self):
        x = [
            0, 0, 1, 0, 0, 1, 1, 0, 1, 1,       # II
            1, 1, 0, 1, 1, 0, 0, 1, 0, 0,       # I
            0, 0, -1, 0, 0, -1, -1, 0, -1, -1,  # IV
            -1, -1, 0, -1, -1, 0, 0, -1, 0, 0   # III
        ]
        y = [
            1, 1, 0, 1, 1, 0, 0, 1, 0, 0,       # II
            0, 0, -1, 0, 0, -1, -1, 0, -1, -1,  # I
            -1, -1, 0, -1, -1, 0, 0, -1, 0, 0,  # IV
            0, 0, 1, 0, 0, 1, 1, 0, 1, 1        # III
        ]
        self.assertEqual(_plan_interpolated_circle(5), (x, y))


if __name__ == "__main__":
    unittest.main()
