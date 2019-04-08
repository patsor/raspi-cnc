#!/usr/bin/env python

from __future__ import print_function

import time
import math
import logging
from argparse import ArgumentParser

class MotionPlanner(object):
    def __init__(self, name, motion_type, step_angle, travel_per_rev, mode, accel, traverse_rate, feed_rate, debug=False):
        self.name = name
        self.motion_type = motion_type
        self.step_angle = step_angle
        self.travel_per_rev = travel_per_rev
        self.mode = mode
        self.accel = accel
        self.logger = logging.getLogger("MotionPlanner")
        self.debug = debug

        self.t_accel = {}
        self.n_accel = {}
        self.t_accel["traverse"] = self.configure_ramp(traverse_rate, "polynomial")
        self.n_accel["traverse"] = len(self.t_accel["traverse"])
        self.t_accel["feed"] = self.configure_ramp(feed_rate, "polynomial")
        self.n_accel["feed"] = len(self.t_accel["feed"])

    def get_motion_type(self):
        """Get motion type of stepper motor"""
        return self.motion_type

    def set_motion_type(self, motion_type):
        """Set motion type of stepper motor"""
        self.motion_type = motion_type

    def calc_steps(self, dist):
        self.logger.debug("{} - Caluclating number of steps".format(self.name))
        n = int(round(abs(dist) * 360.0 / self.step_angle / self.travel_per_rev * self.mode))
        self.logger.debug("{} steps required to reach destination".format(n))
        return n
        
    def plan_line(self, dist):
        step_intervals = []
        n = self.calc_steps(dist)
#        self.logger.debug("{} - Moving {}mm".format(self.name, dist))
        steps_left = n
        step_interval = 0.0002
        
        for i in range(n):
            steps_left -= 1
            
            if i < self.n_accel[self.motion_type]:
                step_interval = self.t_accel[self.motion_type][i]
            if steps_left < self.n_accel[self.motion_type]:
                step_interval = self.t_accel[self.motion_type][steps_left]
            delay = step_interval * 0.5

#            if not self.debug:
#                self.step(delay)
            step_intervals.append(delay)
        return step_intervals
            
    def configure_ramp(self, vm, method="trapezoidal"):
        if method == "trapezoidal":
            return (self._configure_ramp_trapezoidal(vm))
        elif method == "polynomial":
            return (self._configure_ramp_polynomial(vm))

    def _configure_ramp_trapezoidal(self, vm):
        self.logger.info("{} - Generating trapezoidal ramp profile [v_max={}]".format(self.name, vm))
        sqrt = math.sqrt
        # steps per revolution: microstepping mode as factor
        spr = 360.0 / self.step_angle * self.mode
        # Number of steps it takes to move axis 1mm
        steps_per_mm = spr / self.travel_per_rev
        # linear movement along the axes per step
        # angle of rotation (phi) per step in rad: 2 * PI = 360 degrees
        # [rotation_angle = 2 * PI / SPR]
        step_angle_in_rad = 2 * math.pi / spr
        # Convert target velocity from mm/min to rad/s
        cf = vm / 60 * steps_per_mm * step_angle_in_rad
        # Convert acceleration from mm/s^2 to rad/s^2
        accel_fact = self.accel * steps_per_mm * step_angle_in_rad
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
#        print("Max speed [mm/min]: {}".format(v_max))
#        print("Acceleration/Deceleration [mm/s^2]: {}".format(self.accel))
#        print("c{}: {} => Final speed: {}[steps/s], {}[m/s], {}[mm/min], {}[rad/s], {}[rpm]".format(num_steps, cn, step_s, m_s, mm_min, rad_s, rpm))
        return c

    def _configure_ramp_polynomial(self, vm):
        sqrt = math.sqrt
        # steps per revolution: microstepping mode as factor
        spr = 360.0 / self.step_angle * self.mode
        # Number of steps it takes to move axis 1mm
        steps_per_mm = spr / self.travel_per_rev
        # linear movement along the axes per step
        # angle of rotation (phi) per step in rad: 2 * PI = 360 degrees
        # [rotation_angle = 2 * PI / SPR]
        step_angle_in_rad = 2 * math.pi / spr
        # Convert target velocity from mm/min to rad/s
        v3 = vm / 60 * steps_per_mm * step_angle_in_rad
        # Convert acceleration from mm/s^2 to rad/s^2
        accel_in_rad = self.accel * steps_per_mm * step_angle_in_rad
        # Calculation of number of steps needed to accelerate/decelerate
        # Concave segment

        v1 = v3 / 4
        v2 = v3 * 3 / 4
        print("a(T/2) = {}".format(accel_in_rad))
        print("v(0) = 0")
        print("v(P1) = {}".format(v1))
        print("v(P2) = {}".format(v2))
        print("v(T) = {}".format(v3))
        n1 = int(round(v1**2 / (step_angle_in_rad * accel_in_rad)))
        n2 = int(round(v2**2 / (2 * accel_in_rad * step_angle_in_rad))) + n1
        n3 = int(round(2 * v3**3 / (step_angle_in_rad * accel_in_rad**2))) + n2
        print(n1, n2, n3)
        ntotal = n3
        # Add time intervals for steps to achieve linear acceleration

        cn = 0
        an = 0
        period = "none"
        c = []
        for i in range(n3):
            # Concave period of the acceleration curve
            if i <= n1:
                period = "concave"
                an = (i+1) / float(n1+1) * accel_in_rad
                c0 = (2 * step_angle_in_rad / an)**(1./3)
                cn_i_plus_1 = (i + 1)**(1./3)
                cn_i = (i)**(1./3)
                cn = c0 * (cn_i_plus_1 - cn_i)
                c.append(cn)
            # Linear period of the acceleration curve
            elif n1 < i <= n2:
                period = "linear"
                an = accel_in_rad
                c0 = sqrt(2 * step_angle_in_rad / an)
                cn_i_plus_1 = sqrt(i + 1)
                cn_i = sqrt(i)
                # TODO: the linear period underlies some y axis section
                # parameter C has to be found => 2/step_angle?
                ct = c0 * (cn_i_plus_1 - cn_i)
                vt = 1 / ct * step_angle_in_rad - accel_in_rad / (v2 * 2)
                cn = 1 / vt * step_angle_in_rad
                c.append(cn)
            # Convex period of the acceleration curve
            # TODO: not perfectly fitting, needs to be investigated further
            # maybe there is also some y axis section in the opposite direction
            elif n2 < i < n3:
                period = "convex"
                an = ((n3) - (i-n2)) / float(n3) * accel_in_rad
                c0 = (2 * step_angle_in_rad / an)**(1./3)
                cn_i_plus_1 = (i + 1)**(1./3)
                cn_i = (i)**(1./3)
                ct = c0 * (cn_i_plus_1 - cn_i)
                vt = 1 / ct * step_angle_in_rad + accel_in_rad / (v3 * 2)
                cn = 1 / vt * step_angle_in_rad
                c.append(cn)
            print(i, period, an, 1/cn, 1/cn*step_angle_in_rad)
        return c
        
def main():
    step_angle = 1.8
    travel_per_rev = 5.0
    mode = 1
    motion_type = "traverse"
    a = 100.0
    v = 1200.0
    f = 400.0
    debug=False
        
    mp = MotionPlanner(
        "X axis",
        "traverse",
        step_angle,
        travel_per_rev,
        mode,
        a,
        v,
        f,
        debug
    )
    mp.plan_line(10)
#    mp.configure_ramp("scurve", v)


if __name__ == '__main__':
    main()
