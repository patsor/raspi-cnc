class GCode(object):
    def __init__(self, params):
        self.params = params

    def __str__(self):
        string_repr = ""
        for key in ("N", "G", "X", "Y", "Z", "I", "J", "R"):
            val = key + self.params[key] + " " if self.get(key) else ""
            string_repr += val
        return string_repr.strip()

    def get(self, key):
        if key in self.params:
            if key in ("G", "N", "M"):
                return self.params[key]
            else:
                return float(self.params[key])
        else:
            return None

    def __eq__(self, other):
        if not isinstance(other, GCode):
            return False

        return self.params == other.params
