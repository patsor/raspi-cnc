#!/usr/bin/env python

from __future__ import print_function

import sys
import time
from argparse import ArgumentParser
import ConfigParser
from multiprocessing import Process

import RPi.GPIO as GPIO

from nicelog import nprint, nflush
from gpio_handler import GPIOHandler
from stepper import Stepper
from instruction_set import InstructionSet

def move(motor, dist):
    motor.move(dist)

class Router(object):
    def __init__(self, cfg_file, debug=False):
        self.cfg_file = cfg_file
        self.cfg = ConfigParser.ConfigParser()
        self.cfg.read(cfg_file)
        self.debug = debug
        self.handler = GPIOHandler(GPIO.BOARD, False, debug)
        self.configure_motors()

    def configure_motors(self):
        self.gpios_x = [int(x) for x in self.cfg.get('x', 'gpio_pins').split(",")]
        self.gpios_y = [int(x) for x in self.cfg.get('y', 'gpio_pins').split(",")]
        self.gpios_z = [int(x) for x in self.cfg.get('z', 'gpio_pins').split(",")]

        self.handler.set_output_pins(self.gpios_x)
        self.handler.set_output_pins(self.gpios_y)
        self.handler.set_output_pins(self.gpios_z)
        self.handler.default_output_pins(self.gpios_x)
        self.handler.default_output_pins(self.gpios_y)
        self.handler.default_output_pins(self.gpios_z)

        self.pos_x = self.cfg.getfloat('x', 'position')
        self.pos_y = self.cfg.getfloat('y', 'position')
        self.pos_z = self.cfg.getfloat('z', 'position')

        self.mx_normal = self.cfg.getint('x', 'normal_mode')
        self.mx_rapid = self.cfg.getint('x', 'rapid_mode')
        self.my_normal = self.cfg.getint('y', 'normal_mode')
        self.my_rapid = self.cfg.getint('y', 'rapid_mode')
        self.mz_normal = self.cfg.getint('z', 'normal_mode')
        self.mz_rapid = self.cfg.getint('z', 'rapid_mode')
        ax = self.cfg.getfloat('x', 'acceleration_rate')
        ay = self.cfg.getfloat('y', 'acceleration_rate')
        az = self.cfg.getfloat('z', 'acceleration_rate')
        vx = self.cfg.getfloat('x', 'max_velocity')
        vy = self.cfg.getfloat('y', 'max_velocity')
        vz = self.cfg.getfloat('z', 'max_velocity')

        self.x_lim = self.cfg.getfloat('x', 'max_position')
        self.y_lim = self.cfg.getfloat('y', 'max_position')
        self.z_lim = self.cfg.getfloat('z', 'max_position')

        self.s_x = Stepper(
            "Stepper X axis",
            self.mx_normal,
            "CW",
            self.gpios_x,
            ax,
            vx,
            self.debug
        )
        self.s_y = Stepper(
            "Stepper Y axis",
            self.my_normal,
            "CW",
            self.gpios_y,
            ay,
            vy,
            self.debug
        )
        self.s_z = Stepper(
            "Stepper Z axis",
            self.mz_normal,
            "CW",
            self.gpios_z,
            az,
            vz,
            self.debug
        )

#        self.s_x.configure_ramp()
#        self.s_y.configure_ramp()
#        self.s_z.configure_ramp()
        
        self.motors = [self.s_x, self.s_y, self.s_z]
        
    def save_positions(self):
        self.cfg.set('x', 'position', self.pos_x)
        self.cfg.set('y', 'position', self.pos_y)
        self.cfg.set('z', 'position', self.pos_z)
        with open(self.cfg_file, "wb") as configfile:
            self.cfg.write(configfile)
        #        self.cfg.save_cfg()
        
    def route(self, instruction_file):
        inst_set = InstructionSet(instruction_file, self.x_lim, self.y_lim, self.z_lim)
        for command in inst_set.instructions:
            # vectors for axis movement
            x = y = z = 0.0
            dx = dy = dz = 0.0
            for (prefix, val) in command:
                if prefix == "G":
                    if val == "00":
                        self.s_x.set_mode(self.mx_rapid)
                        self.s_y.set_mode(self.my_rapid)
                        self.s_z.set_mode(self.mz_rapid)
                    else:
                        self.s_x.set_mode(self.mx_normal)
                        self.s_y.set_mode(self.my_normal)
                        self.s_z.set_mode(self.mz_normal)
#                        self.s_x.configure_ramp()
#                        self.s_y.configure_ramp()
#                        self.s_z.configure_ramp()
                elif prefix == "X":
                    x = float(val)
                    dx = x - self.pos_x
                elif prefix == "Y":
                    y = float(val)
                    dy = y - self.pos_y
                elif prefix == "Z":
                    z = float(val)
                    dz = -z + self.pos_z
            delta = [dx, dy, dz]
            text="Calculating motion vector"
            nprint(text)
#            print("Motion Vector:")
#            print("(x)   (dx) = ({:>6.2f})   ({:>7.2f})   ({:>6.2f})".format(self.pos_x, dx, x))
#            print("(y) + (dy) = ({:>6.2f}) + ({:>7.2f}) = ({:>6.2f})".format(self.pos_y, dy, y))
#            print("(z)   (dz) = ({:>6.2f})   ({:>7.2f})   ({:>6.2f})".format(self.pos_z, dz, z))
            nflush(text)
            # Starting axis movement as parallel processes
            procs = []
            for i in range(3):
                if delta[i] < 0:
                    self.motors[i].set_direction("CCW")
                elif delta[i] > 0:
                    self.motors[i].set_direction("CW")
                else:
                    continue
                proc = Process(target=move, args=(self.motors[i], delta[i]))
                procs.append(proc)

            for proc in procs:
                proc.start()

            for proc in procs:
                proc.join()

            self.pos_x += dx
            self.pos_y += dy
            self.pos_z -= dz

        self.handler.default_output_pins(self.gpios_x)
        self.handler.default_output_pins(self.gpios_y)
        self.handler.default_output_pins(self.gpios_z)
        self.handler.cleanup()
        


def main():
    parser = ArgumentParser(description='Process materials')
    parser.add_argument('-i', '--input', dest='input', help='input g-code file', required=True)
    parser.add_argument('-d', '--debug', dest='debug', action='store_true', help='Set debug mode')
    args = parser.parse_args()
#    debug = args.debug
    instruction_file = args.input
    # GPIOs: [DIR,STP,M0,M1,M2]
#    cfg = Config("settings.cfg")
    cfg_file = "settings.cfg"

    router = Router(cfg_file, args.debug)
    router.route(instruction_file)
    router.save_positions()


if __name__ == '__main__':
    main()
