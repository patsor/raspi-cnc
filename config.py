#!/usr/bin/env python

from argparse import ArgumentParser

class Config(object):
    def __init__(self,cfg_file):
        self.cfg_file = cfg_file
        self.cfg = {}
        self.read_cfg()

    def read_cfg(self):
        with open(self.cfg_file) as inf:
            for line in inf:
                if line[0] == "[":
#                    section = line.strip("[","]")
                    section = line.rstrip().translate(None, "[]")
#                    print section
                    self.cfg[section] = {}
                elif line[0] not in ["\n","["]:
                    key,val = line.rstrip().split("=")
#                    print elements
#                    ele = keyval[0]
#                    val = keyval[1]
                    self.cfg[section][key] = val

    def save_cfg(self):
        outf = open(self.cfg_file,"w")
        for section in self.cfg:
            outf.write("[" + section + "]\n")
            for key in self.cfg[section]:
                outf.write(key + "=" + str(self.cfg[section][key]) + "\n")
            outf.write("\n")

        outf.close()

    def get(self,section,ele):
        return self.cfg[section][ele]

    def set(self,section,ele,val):
        self.cfg[section][ele] = val


def main():
    parser = ArgumentParser(description="Handles configuration")
    parser.add_argument('-i','--input',dest='input',help='Specify input config file')
    args = parser.parse_args()

    c = Config(args.input)
    print c.get('general','logfile')
    print c.get('gpio','pins_x')
    c.set('gpio','pins_r','4,5,6,7')
    print c.get('gpio','pins_r')
    c.save_cfg()

if __name__ == '__main__':
    main()
