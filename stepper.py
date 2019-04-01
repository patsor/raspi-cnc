#!/usr/bin/env python

from __future__ import print_function

import time
import math
from argparse import ArgumentParser

import RPi.GPIO as GPIO

from nicelog import nprint, nflush, ninfo

def busy_wait(dt):
    current_time = time.time()
    while (time.time() < current_time + dt):
        pass

class Stepper(object):
    def __init__(self, name, mode, direction, gpios, a, v, debug=False):
        self.name = name
        self.mode = mode
        self.direction = direction
        self.gpios = gpios
        self.a = a
        self.v = v
        self.debug = debug
        # Microstepping modes of DRV8825
        # Microstepping mode 1/n: M2, M1, M0
        # Example: 1/2 (Half step): M2=0, M1=0, M0=1
        self.modes = {
            1: (0, 0, 0),
            2: (0, 0, 1),
            4: (0, 1, 0),
            8: (0, 1, 1),
            16: (1, 0, 0),
            32: (1, 1, 0)
        }
        
        # Microstepping modes of TB67S249FTG
        # Microstepping mode 1/n: M2, M1, M0
        #self.modes = {
        #    0: (0, 0, 0),
        #    1: (1, 0, 0),
        #    2: (0, 1, 0),
        #    4: (1, 1, 0),
        #    8: (1, 0, 1),
        #    16: (0, 1, 1),
        #    32: (1, 1, 1)
        #}

        self.dirs = {
            "CW": False,
            "CCW": True
        }
        
        self.set_mode(mode, initial=True)
        self.set_direction(direction, initial=True)
        # Calculate ramping profiles for all possible modes
        self.c = {}
        self.n_accel = {}
        for key in self.modes:
            (self.c[key], self.n_accel[key]) = self.configure_ramp(key)

    def get_mode(self):
        """Get mode of stepper motor"""
        return self.mode

    def set_mode(self, mode, initial=False):
        """Set mode of stepper motor"""
        # Do not change mode if input mode equals current mode
        if self.mode == mode and not initial:
            return
        if mode not in self.modes:
            raise ValueError("Mode not available: {}".format(mode))
        bits = self.modes[mode]
        text="{} - Setting Microstepping Mode: 1/{} {}".format(self.name, mode, bits)
        nprint(text)

        if not self.debug:
            for i in range(3):
                GPIO.output(self.gpios[i+2], bits[i])
                time.sleep(0.1)
        self.mode = mode
        nflush(text)

    def get_direction(self):
        """Get direction of stepper motor"""
        return self.direction
        
    def set_direction(self, direction, initial=False):
        """Set direction of stepper motor"""
        # Do not change direction if input direction equals current direction
        if self.direction == direction and not initial:
            return
        text="{} - Setting direction: {}".format(self.name, direction)
        nprint(text)
        if not self.debug:
            GPIO.output(self.gpios[0], self.dirs[direction])
            time.sleep(0.1)
        self.direction = direction
        nflush(text)

    def step(self, delay):
        GPIO.output(self.gpios[1], True)
        busy_wait(delay)
        GPIO.output(self.gpios[1], False)
        busy_wait(delay)

    def calc_steps(self, dist):
        text="{} - Caluclating number of steps".format(self.name)
        nprint(text)
        steps = int(round(abs(dist) * 40.0 * self.mode))
        nflush(text)
        ninfo("{} steps required to reach destination".format(steps))
        return steps

    def move(self, dist):
        steps = self.calc_steps(dist)
        text="{} - Moving {}mm".format(self.name, dist)
        nprint(text)
        steps_left = steps
        step_interval = 0.0002
        
        for i in range(steps):
            steps_left -= 1

            if i < self.n_accel[self.mode]:
                step_interval = self.c[self.mode][i]
            if steps_left < self.n_accel[self.mode]:
                step_interval = self.c[self.mode][steps_left]
            delay = step_interval * 0.5
            
            if not self.debug:
                self.step(delay)
            else:
                busy_wait(step_interval)
        nflush(text)

    def configure_ramp(self, mode, method="trapezoidal"):
        if method == "trapezoidal":
            return (self._configure_ramp_trapezoidal(mode))
        elif method == "paraboloid":
            return (self._configure_ramp_paraboloid(mode))

    def _configure_ramp_trapezoidal(self, mode):
        text="{} - Generating trapezoidal ramp profile".format(self.name)
        nprint(text)
        sqrt = math.sqrt
        # steps per revolution: microstepping mode as factor
        spr = 200 * mode
        # Number of steps it takes to move axis 1mm
        steps_per_mm = spr / 5
        # linear movement along the axes per step
        # angle of rotation (phi) per step in rad: 2 * PI = 360 degrees
        # [rotation_angle = 2 * PI / SPR]
        step_angle_in_rad = 2 * math.pi / spr
        # Convert target velocity from mm/min to rad/s
        cf = self.v / 60 * steps_per_mm * step_angle_in_rad
        # Convert acceleration from mm/s^2 to rad/s^2
        accel_fact = self.a * steps_per_mm * step_angle_in_rad
        # Calculation of number of steps needed to accelerate/decelerate
        # vf = final velocity (rad/s)
        # a = acceleration (rad/s^2)
        # [n_steps = vf^2 / (2 * rotation_angle * a)]
        num_steps = int(round(cf * cf / (2 * step_angle_in_rad * accel_fact)))
        # Calculation of initial step duration during acceleration/deceleration ph\ase
        # [c0 = (f=1) * sqrt(2 * rotation_angle / a)]
        c0 = sqrt(2 * step_angle_in_rad / accel_fact)
        # Add time intervals for steps to achieve linear acceleration
        c = [c0]
        cn = c0
        for i in range(1, num_steps):
            cn = c0 * (sqrt(i+1) - sqrt(i))
            c.append(cn)
            # Get the total duration of all acceleration steps
            # should be [t_a = cf/a]
#        c_total = sum(c)
#        step_s = 1.0 / cn
#        rad_s = step_angle_in_rad / cn
#        rpm = rad_s * 9.55
#        mm_min = rpm * 5
#        mm_s = mm_min / 60
#        m_s = mm_s / 1000
#        print("Motor: {}".format(self.name))
#        print("Steps per revolution: {}".format(spr))
#        print("Initial step duration c0 [s]: {}".format(c0))
#        print("Number of steps to accelerate/decelerate: {}".format(num_steps))
#        print("Acceleration/Deceleration duration [s]: {}".format(c_total))
#        print("Max speed [mm/min]: {}".format(self.v))
#        print("Acceleration/Deceleration [mm/s^2]: {}".format(self.a))
#        print("c{}: {} => Final speed: {}[steps/s], {}[m/s], {}[mm/min], {}[rad/s], {}[rpm]".format(num_steps, cn, step_s, m_s, mm_min, rad_s, rpm))
        nflush(text)
        return (c, num_steps)
        
    def _configure_ramp_paraboloid(self):
        text="{} - Generating trapezoidal ramp profile".format(self.name)
        nprint(text)
        sqrt = math.sqrt
        # steps per revolution: microstepping mode as factor
        spr = 200 * self.motors[0].get_mode()
        # Number of steps it takes to move axis 1mm
        steps_per_mm = spr / 5
        # linear movement along the axes per step
        # angle of rotation (phi) per step in rad: 2 * PI = 360 degrees
        # [rotation_angle = 2 * PI / SPR]
        step_angle_in_rad = 2 * math.pi / spr
        # Convert target velocity from mm/min to rad/s
        cf = self.max_velocity / 60 * steps_per_mm * step_angle_in_rad
        # Convert acceleration from mm/s^2 to rad/s^2
        accel_fact = self.accel_rate * steps_per_mm * step_angle_in_rad
        
        # Calculation of initial step duration during acceleration/deceleration phase
        # [c0 = (f=1) * sqrt(2 * rotation_angle / a)]
        c0 = sqrt(2 * step_angle_in_rad / accel_fact)
        c = [c0]
        n1 = 0
        n2 = int(round(cf * cf / (2 / math.e * step_angle_in_rad * accel_fact)))
        cn = 0
        c_trans = c0
        for i in range(1, n2):
            #            cn_old = c0 * (sqrt(i+1) - sqrt(i))
            if i >= n1:
                # linear factor to decrease acceleration upon threshold n1
                # ranges from 1 to 0
                factor = float(n2*2 - i)/(n2*2 - n1)
                c_trans = c0 * sqrt(math.e / 2 / factor)
                cn = c_trans * (sqrt(i+1) - sqrt(i))
            else:
                cn = c0 * (sqrt(i+1) - sqrt(i))
            c.append(cn)
#        c_total = sum(c)
#        step_s = 1.0 / cn
#        rad_s = step_angle_in_rad / cn
#        rpm = rad_s * 9.55
#        mm_min = rpm * 5
#        mm_s = mm_min / 60
#        m_s = mm_s / 1000
#        print("Steps per revolution: {}".format(spr))
#        print("Initial step duration c0 [s]: {}".format(c0))
#        print("Number of steps to accelerate/decelerate: {}".format(n2))
#        print("Acceleration/Deceleration duration [s]: {}".format(c_total))
#        print("Max speed [mm/min]: {}".format(self.max_velocity))
#        print("Acceleration/Deceleration [mm/s^2]: {}".format(self.accel_rate))
#        print("c{}: {} => Final speed: {}[steps/s], {}[m/s], {}[mm/min], {}[rad/s], {}[rpm]".              format(i, cn, step_s, m_s, mm_min, rad_s, rpm))
        nflush(text)
        return (c, n2)
        
