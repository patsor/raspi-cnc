class GCode(object):
    def __init__(self, params):
        self._params = params

    def __str__(self):
        """String representation of parameter dictionary."""
        string_repr = ""
        for key in ("N", "G", "X", "Y", "Z", "I", "J", "R"):
            val = key + self._params[key] + " " if self.get(key) is not None else ""
            string_repr += val
        return string_repr.strip()

    def get(self, key):
        """Gets parameter from paramters list."""
        if key in self._params:
            if key in ("G", "N", "M"):
                return self._params[key]
            else:
                return float(self._params[key])
        else:
            return None

    def __eq__(self, other):
        """Method to allow comparison to other gcode objects.
        Required for unit testing."""
        if not isinstance(other, GCode):
            return False

        return self._params == other._params
