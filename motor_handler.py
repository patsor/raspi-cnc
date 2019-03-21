#!/usr/bin/env python

from __future__ import print_function
import time
import math
from argparse import ArgumentParser

import RPi.GPIO as GPIO

from stepper import Stepper

class MotorHandler(object):
    def __init__(self, motors, accel_rate, max_velocity, debug=False):
        self.debug = debug
        self.motors = motors
        self.accel_rate = accel_rate
        self.max_velocity = max_velocity
        self.configure_ramp()

    def configure_ramp(self):
        sqrt = math.sqrt
        # Convert units from mm/min to mm/s
        final_velocity = self.max_velocity / 60
        # Timer frequency f in Hz
        step_frequency = 1
        # steps per revolution: microstepping mode as factor
        spr = 200 * self.motors[0].get_mode()
        # linear movement along the axes per step
        # angle of rotation (phi) per step in rad: 2 * PI = 360 degrees
        # [rotation_angle = 2 * PI / SPR]
        step_angle_in_rad = 2 * math.pi / spr
        # Calculation of number of steps needed to accelerate/decelerate
        # vf = final velocity (m/s)
        # a = acceleration (m/s^2)
        # [n_steps = vf^2 / (2 * rotation_angle * a)]
        num_steps = int(round(final_velocity * final_velocity / (2 * step_angle_in_rad * self.accel_rate)))
        # Calculation of initial step duration during acceleration/deceleration phase
        # [c0 = f * sqrt(2 * rotation_angle / a)]
        c0 = step_frequency * sqrt(2 * step_angle_in_rad / self.accel_rate)
        # Add time intervals for steps to achieve linear acceleration
        c = [c0]
        cn = 0
        for i in range(1, num_steps):
            cn = c0 * (sqrt(i+1) - sqrt(i))
            c.append(cn)
        step_s = 1.0 / cn
        rad_s = step_angle_in_rad / cn
        rpm = rad_s * 9.55
        mm_min = rpm * 5
        mm_s = mm_min / 60
        m_s = mm_s / 1000
        print("Steps per revolution: {}".format(spr))
        print("Initial step duration c0 [s]: {}".format(c0))
        print("Number of steps to accelerate/decelerate: {}".format(num_steps))
        print("Max speed [mm/min]: {}".format(self.max_velocity))
        print("Acceleration/Deceleration [m/s^2]: {}".format(self.accel_rate))
        print("c{}: {} => Final speed: {}[steps/s], {}[m/s], {}[mm/min], {}[rad/s], {}[rpm]".format(i, cn, step_s, m_s, mm_min, rad_s, rpm))
        self.c = c
        self.num_steps_accel = num_steps

    def calc_steps(self, dist, motor):
        if dist < 0:
            motor.set_direction(True)
        elif dist > 0:
            motor.set_direction(False)
        steps = int(round(abs(dist) * 40 * motor.get_mode()))
        print("{} - Moving {}mm (Steps: {})".format(motor.name, dist, steps))
        return steps

    def move(self, dist, motor):
        steps = self.calc_steps(dist, motor)
        steps_left = steps
        step_interval = 0.0002

        for i in range(steps):
            steps_left -= 1

            if i < self.num_steps_accel:
                step_interval = self.c[i]
            if steps_left < self.num_steps_accel:
                step_interval = self.c[steps_left]
            delay = step_interval * 0.5

            if not self.debug:
                motor.step(delay)

def main():
    parser = ArgumentParser(description="Handles motor movement")
    parser.add_argument('-n', '--dist', dest='distance', nargs='+', type=int, help='Specify distance in mm the motor shall move')
    args = parser.parse_args()
    s1 = Stepper("X axis", 2, True, [0, 1, 2, 3, 4], True)
    s2= Stepper("Y axis", 2, True, [0, 1, 2, 3, 4], True)
    s3 = Stepper("Z axis", 2, True, [0, 1, 2, 3, 4], True)
    m = MotorHandler([s1, s2, s3], 200, 200, 25, True)
    m.move(args.dist, s1)



if __name__ == '__main__':
    main()
