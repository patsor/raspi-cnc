class GCodeError(Exception):
    """Base class for exceptions while parsing gcode."""
    pass


class GCodeNotFoundError(GCodeError):
    """Exception raised if G or M not present in gcode."""

    def __init__(self, expression, message):
        self.expression = expression
        self.message = message


class DuplicateGCodeError(GCodeError):
    """Exception raised if gcode contains duplicate keys."""

    def __init__(self, expression, message):
        self.expression = expression
        self.message = message


class InvalidGCodeError(GCodeError):
    """Exception raised if param in gcode is invalid."""

    def __init__(self, expression, message):
        self.expression = expression
        self.message = message


class MissingGCodeError(GCodeError):
    """Exception raised when G or M missing in gcode."""

    def __init__(self, expression, message):
        self.expression = expression
        self.message = message


class UnsupportedGCodeError(GCodeError):
    """Exception raised when gcode is not (yet) supported."""

    def __init__(self, expression, message):
        self.expression = expression
        self.message = message


class GCodeOutOfBoundsError(GCodeError):
    """Exception raised when gcode is passes axes limits."""

    def __init__(self, expression, message):
        self.expression = expression
        self.message = message
