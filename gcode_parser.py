#!/usr/bin/env python

import config as cfg
from gcode import GCode

from gcode_exceptions import DuplicateGCodeError, GCodeNotFoundError, InvalidGCodeError, MissingGCodeError, UnsupportedGCodeError, GCodeOutOfBoundsError

supported_gcodes = {
    "00": "Rapid positioning",
    "01": "Linear interpolation",
    "02": "Circular interpolation, clockwise",
    "17": "XY plane selection",
    "18": "XZ plane selection",
    "19": "YZ plane selection",
    "28": "Return to home position",
}


def is_number(s):
    """Checks if a string is a number."""
    try:
        float(s)
        return True
    except ValueError:
        return False


class GCodeParser(object):

    @ staticmethod
    def read_lines(gcode_file):
        """Parses gcode file and creates gcode list."""
        gcode_list = []
        with open(gcode_file) as inf:
            for line in inf:
                params = GCodeParser.parse_line(line)
                if params:
                    gcode = GCode(params)
                    gcode_list.append(gcode)
        return gcode_list

    @ staticmethod
    def parse_line(line):
        """Parses one line from gcode file."""
        line = line.strip()
        params = {}
        if not line:
            return None
        if line[0] == "%":
            return None
        elements = line.upper().split()
        for ele in elements:
            key = ele[0]
            val = ele[1:]

            # Check if there is already a parameter with name 'key'
            if key in params:
                raise DuplicateGCodeError(line, "Duplicate parameter")

            # Check if parameter is in [A-Z]
            if not key.isalpha():
                raise InvalidGCodeError(line, "Invalid parameter")

            # Check if parameter value is a number
            if not is_number(val):
                raise InvalidGCodeError(line, "Invalid parameter value")

            # Check if X, Y, Z parameters fall in axis range
            if key in ("X", "Y", "Z"):
                limits = cfg.axes[key]["limits"]
                if float(val) < limits[0] or float(val) > limits[1]:
                    raise GCodeOutOfBoundsError(
                        line, "GCode out of bounds")

            # Check if GCode is supported
            if key == "G" and val not in supported_gcodes:
                raise UnsupportedGCodeError(line, "Unsupported G-code")

            # Add parameter to parameter list
            params[key] = val

        # Check if GCode contains either G or M
        if not any(key in params for key in ("G", "M")):
            raise MissingGCodeError(line, "No command found")

        # Check that there is only one of G or M within GCode
        if all(key in params for key in ("G", "M")):
            raise DuplicateGCodeError(line, "G and M code found")

        if "G" in params:
            # Check if linear interpolation has valid command
            if params["G"] == "01":
                if len([key for key in ("X", "Y", "Z") if key in params]) != 2:
                    raise InvalidGCodeError(line, "Either XY, XZ, YZ allowed")
            # Check if circular interpolation has valid command
            elif params["G"] == "02":
                if not "R" in params:
                    raise InvalidGCodeError(line, "Missing R parameter")
            elif params["G"] in ("17", "18", "19"):
                if any(key in params for key in ("X", "Y", "Z")):
                    raise InvalidGCodeError(
                        line, "XYZ not allowed during plane selection")
            elif params["G"] == "28":
                if any(key in params for key in ("X", "Y", "Z")):
                    raise InvalidGCodeError(
                        line, "XYZ not allowed during homing")

        return params
