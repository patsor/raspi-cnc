#!/usr/bin/env python

from __future__ import print_function

import sys
import time
from argparse import ArgumentParser
import ConfigParser

import RPi.GPIO as GPIO

from gpio_handler import GPIOHandler
from stepper import Stepper
from motor_handler import MotorHandler
from instruction_set import InstructionSet
#from config import Config

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
        accel = int(self.cfg.get('general', 'accel'))
        decel = int(self.cfg.get('general', 'decel'))
        speed = int(self.cfg.get('general', 'max_speed'))
        self.motor_handler = MotorHandler(self.motors, accel, decel, speed, self.debug)
        
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
            delta_x = delta_y = delta_z = 0
            for (prefix, val) in command:
                if prefix == "G":
                    if val == "00":
                        self.s_x.set_mode(self.rapid_feed)
                        self.s_y.set_mode(self.rapid_feed)
                        self.s_z.set_mode(self.rapid_feed)
                    else:
                        self.s_x.set_mode(self.normal_feed)
                        self.s_y.set_mode(self.normal_feed)
                        self.s_z.set_mode(self.normal_feed)
                elif prefix == "X":
                    delta_x = int(val) - self.pos_x
                    self.pos_x += delta_x
                elif prefix == "Y":
                    delta_y = int(val) - self.pos_y
                    self.pos_y += delta_y
                elif prefix == "Z":
                    delta_z = - int(val) + self.pos_z
                    self.pos_z -= delta_z
                    
            print("Move: [X={}mm, Y={}mm, Z={}mm], Microstepping: 1/{}".format(delta_x, delta_y, delta_z, self.s_x.get_mode()))
            self.motor_handler.move([delta_x, -delta_y, delta_z])
#            self.s_x = Stepper(1,"Stepper X axis",2,1,self.gpios_x,delta_x,self.debug)
#            self.s_y = Stepper(2,"Stepper Y axis",2,1,self.gpios_y,delta_y,self.debug)
#            self.s_z = Stepper(3,"Stepper Z axis",2,1,self.gpios_z,delta_z,self.debug)

#            self.s_x.move(delta_x)
#            self.s_y.move(delta_y)
#            self.s_z.move(delta_z)
            

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
