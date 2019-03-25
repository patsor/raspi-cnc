#!/usr/bin/env python

from __future__ import print_function

import sys
import time
from argparse import ArgumentParser
import ConfigParser
from multiprocessing import Process

import RPi.GPIO as GPIO

from gpio_handler import GPIOHandler
from stepper import Stepper
from motor_handler import MotorHandler
from instruction_set import InstructionSet
#from config import Config

def move(motor_handler, dist, motor):
    motor_handler.move(dist, motor)

class Router(object):
    def __init__(self, cfg_file, rapid_feed, normal_feed, debug=False):
        self.cfg_file = cfg_file
        self.cfg = ConfigParser.ConfigParser()
        self.cfg.read(self.cfg_file)
        self.rapid_feed = rapid_feed
        self.normal_feed = normal_feed
        self.debug = debug
        self.handler = GPIOHandler(GPIO.BOARD, False, self.debug)
        self.configure_motors()

    def configure_motors(self):
        self.gpios_x = [int(x) for x in self.cfg.get('gpio', 'pins_x').split(",")]
        self.gpios_y = [int(x) for x in self.cfg.get('gpio', 'pins_y').split(",")]
        self.gpios_z = [int(x) for x in self.cfg.get('gpio', 'pins_z').split(",")]

        self.handler.set_output_pins(self.gpios_x)
        self.handler.set_output_pins(self.gpios_y)
        self.handler.set_output_pins(self.gpios_z)
        self.handler.default_output_pins(self.gpios_x)
        self.handler.default_output_pins(self.gpios_y)
        self.handler.default_output_pins(self.gpios_z)

        self.pos_x = int(self.cfg.get('positions', 'x'))
        self.pos_y = int(self.cfg.get('positions', 'y'))
        self.pos_z = int(self.cfg.get('positions', 'z'))
        
        self.s_x = Stepper(
            "Stepper X axis",
            2,
            1,
            self.gpios_x,
            self.debug
        )
        self.s_y = Stepper(
            "Stepper Y axis",
            2,
            1,
            self.gpios_y,
            self.debug
        )
        self.s_z = Stepper(
            "Stepper Z axis",
            2,
            1,
            self.gpios_z,
            self.debug
        )
        self.motors = [self.s_x, self.s_y, self.s_z]
        accel_rate = int(self.cfg.get('general', 'acceleration_rate'))
        max_velocity = int(self.cfg.get('general', 'max_velocity'))
        self.motor_handler = MotorHandler(self.motors, accel_rate, max_velocity, self.debug)
        
    def save_positions(self):
        self.cfg.set('positions', 'x', self.pos_x)
        self.cfg.set('positions', 'y', self.pos_y)
        self.cfg.set('positions', 'z', self.pos_z)
        with open(self.cfg_file, "wb") as configfile:
            self.cfg.write(configfile)
        #        self.cfg.save_cfg()
        
    def route(self, instruction_file):
        inst_set = InstructionSet(instruction_file)
        for command in inst_set.instructions:
            # vectors for axis movement
            dx = dy = dz = 0
            for (prefix, val) in command:
                if prefix == "G":
                    if val == "00":
                        self.s_x.set_mode(self.rapid_feed)
                        self.s_y.set_mode(self.rapid_feed)
                        self.s_z.set_mode(self.rapid_feed)
                        self.motor_handler.configure_ramp_smooth()
                    else:
                        self.s_x.set_mode(self.normal_feed)
                        self.s_y.set_mode(self.normal_feed)
                        self.s_z.set_mode(self.normal_feed)
                        self.motor_handler.configure_ramp_smooth()
                elif prefix == "X":
                    dx = int(val) - self.pos_x
                    self.pos_x += dx
                elif prefix == "Y":
                    dy = int(val) - self.pos_y
                    self.pos_y += dy
                elif prefix == "Z":
                    dz = -int(val) + self.pos_z
                    self.pos_z -= dz
                    
            print("Move: [X={}mm, Y={}mm, Z={}mm], Microstepping: 1/{}".format(dx, dy, dz, self.s_x.get_mode()))
            
            # Starting axis movement as parallel processes
            procs = []
            px = Process(target=move, args=(self.motor_handler, dx, self.s_x))
            py = Process(target=move, args=(self.motor_handler, -dy, self.s_y))
            pz = Process(target=move, args=(self.motor_handler, dz, self.s_z))
            procs.append(px)
            procs.append(py)
            procs.append(pz)

            for proc in procs:
                proc.start()

            for proc in procs:
                proc.join()

        self.handler.default_output_pins(self.gpios_x)
        self.handler.default_output_pins(self.gpios_y)
        self.handler.default_output_pins(self.gpios_z)
        self.handler.cleanup()
        


def main():
    parser = ArgumentParser(description='Process materials')
    parser.add_argument('-i', '--input', dest='input', help='input g-code file', required=True)
    parser.add_argument('-d', '--debug', dest='debug', action='store_true', help='Set debug mode')
    parser.add_argument('-r', '--rapid-feed', dest='rapid_feed', type=int, choices=[1, 2, 4], help='Set rapid feed mode', default=2)
    parser.add_argument('-n', '---normal-feed', dest='normal_feed', type=int, choices=[8, 16, 32], help='Set normal feed mode', default=8)
    args = parser.parse_args()
#    debug = args.debug
    instruction_file = args.input
    # GPIOs: [DIR,STP,M0,M1,M2]
#    cfg = Config("settings.cfg")
    cfg_file = "settings.cfg"


    
    router = Router(cfg_file, args.rapid_feed, args.normal_feed, args.debug)
    router.route(instruction_file)
    router.save_positions()


if __name__ == '__main__':
    main()
