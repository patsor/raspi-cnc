#!/usr/bin/env python

__version__ = "0.1"

class InstructionSet(object):
    def __init__(self, infile):
        self.infile = infile
        self.valid_g_codes = {
            "00": "Rapid positioning",
            "01": "Linear interpolation"
        }
        self.instructions = self.read_gfile()
        
    def read_gfile(self):
        commands = []
        with open(self.infile) as inf:
            for i, line in enumerate(inf):
                if line.startswith("%"):
                    continue
                code_blocks = []
                elements = line.rstrip().split(" ")
                for ele in elements:
                    prefix = ele[0]
                    val = ele[1:]
                    code_blocks.append((prefix, val))
                if self.is_valid(code_blocks):
                    commands.append(code_blocks)
                else:
                    raise ValueError("Invalid Instruction in line {} of {}".format(i, self.infile))
        return commands
                
    def is_valid(self, code_blocks):
        for (prefix, val) in code_blocks:
            if prefix == "N":
                if int(val) < 0:
                    return False
            elif prefix == "G":
                if val not in self.valid_g_codes:
                    return False
            elif prefix == "X":
                if int(val) < 0:
                    return False
            elif prefix == "Y":
                if int(val) < 0:
                    return False
            elif prefix == "Z":
                if int(val) > 0:
                    return False
        return True
