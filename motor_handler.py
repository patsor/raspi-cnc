#!/usr/bin/env python

from __future__ import print_function
import time
import math
from argparse import ArgumentParser

import RPi.GPIO as GPIO

from stepper import Stepper

class MotorHandler(object):
    def __init__(self, motors, accel, decel, max_speed, debug=False):
        self.motors = motors
        self.accel = accel
        self.decel = decel
        self.max_speed = max_speed
        self.spr = 200 * self.motors[0].mode
        print("Steps per round: {}".format(self.spr))
        self.debug = debug
        self.c_acc, self.num_steps_accel = self.configure_acc_dec(self.accel)
        self.c_dec, self.num_steps_decel = self.configure_acc_dec(self.decel)

    def configure_acc_dec(self, accel_decel):
        c = []
        cn = 0
        sqrt = math.sqrt
#        step_frequency = float(self.max_speed) / accel_decel
        step_frequency = 1
        movement_per_step = 5.0 / self.spr
        step_angle_in_rad = 2 * math.pi / self.spr
        num_steps = int(round(self.max_speed * self.max_speed / (2 * step_angle_in_rad * accel_decel)))
        c0 = step_frequency * sqrt(2 * step_angle_in_rad / accel_decel)
        c.append(c0)

        print("c0: {}".format(c0))
        print("Number of steps to accelerate/decelerate: {}".format(num_steps))
        print("Max speed: {}".format(self.max_speed))
        print("Acceleration/Deceleration: {}".format(accel_decel))
        print("Step frequency: {}".format(step_frequency))
        for i in range(1, num_steps):
            cn = c0 * (sqrt(i+1) - sqrt(i))
            c.append(cn)
        step_s = 1.0 / cn
        rad_s = step_angle_in_rad / cn
        rpm = rad_s * 9.55
        mm_min = rpm * 5
        mm_s = mm_min / 60
        m_s = mm_s / 1000
        print("c{}: {} => Final speed: {}[steps/s], {}[m/s], {}[mm/min], {}[rad/s], {}[rpm]".format(i, cn, step_s, m_s, mm_min, rad_s, rpm))
        return (c, num_steps)

    def calc_steps_round_robin(self, dist_arr):
        steps = []
        for i, dist in enumerate(dist_arr):
            if dist < 0:
                self.motors[i].set_direction(True)
            elif dist > 0:
                self.motors[i].set_direction(False)
#            steps[i] = int(round(abs(dist)*40*self.motors[i].mode))
            steps.append(int(round(abs(dist) * 40 * self.motors[i].get_mode())))
            print("{} - Moving {}mm (Steps: {})".format(self.motors[i].name, dist, steps[i]))
        return steps

    def calc_steps(self, dist, motor):
        if dist < 0:
            motor.set_direction(True)
        elif dist > 0:
            motor.set_direction(False)
        steps = int(round(abs(dist) * 40 * motor.get_mode()))
        print("{} - Moving {}mm (Steps: {})".format(motor.name, dist, steps))
        return steps
    
    def move_round_robin(self, dist_arr):
        steps = self.calc_steps(dist_arr)
        max_steps = max(steps)
        steps_left = max_steps
        step_interval = 0.0002
        num_motors = len(steps)

#        print num_motors
        for i in range(max_steps):
            steps_left -= 1

            if i < self.num_steps_accel:
                step_interval = self.c_acc[i]
            if steps_left < self.num_steps_decel:
                step_interval = self.c_dec[steps_left]
            on_time = step_interval * 0.5
            off_time = step_interval - on_time

            for j, motor in enumerate(self.motors):
                if steps[j] > 0:
                    steps[j] -= 1
                    if not self.debug:
                        motor.step(on_time, off_time)

    def move(self, dist, motor):
        steps = self.calc_steps(dist, motor)
        steps_left = steps
        step_interval = 0.0002

#        print num_motors
        for i in range(steps):
            steps_left -= 1

            if i < self.num_steps_accel:
                step_interval = self.c_acc[i]
            if steps_left < self.num_steps_decel:
                step_interval = self.c_dec[steps_left]
            on_time = step_interval * 0.5
            off_time = step_interval - on_time

            if not self.debug:
                motor.step(on_time, off_time)

def main():
    parser = ArgumentParser(description="Handles motor movement")
    parser.add_argument('-n', '--steps', dest='steps', nargs='+', type=int, help='Specify number of motor steps')
    args = parser.parse_args()
    s1 = Stepper("X axis", 2, True, [0, 1, 2, 3, 4], True)
    s2= Stepper("Y axis", 2, True, [0, 1, 2, 3, 4], True)
    s3 = Stepper("Z axis", 2, True, [0, 1, 2, 3, 4], True)
    m = MotorHandler([s1, s2, s3], 200, 200, 75, True)
    m.move(args.steps)



if __name__ == '__main__':
    main()