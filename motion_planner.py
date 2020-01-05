#!/usr/bin/env python

from __future__ import print_function

import time
import math
import logging
from argparse import ArgumentParser


class MotionPlanner(object):
    def __init__(self, motion_type, ramp_type, step_angle, travel_per_rev, mode, accel, traverse_rate, feed_rate, debug=False):
        self.motion_type = motion_type
        self.ramp_type = ramp_type
        self.step_angle = step_angle
        self.travel_per_rev = travel_per_rev
        self.mode = mode
        self.accel = accel
        self.logger = logging.getLogger("MotionPlanner")
        self.debug = debug

        self.t_accel = {}
        self.n_accel = {}

        (step_timings, c_total) = self.configure_ramp(traverse_rate, ramp_type)
        self.t_accel["traverse"] = step_timings
        self.n_accel["traverse"] = len(step_timings)

        (step_timings, c_total) = self.configure_ramp(feed_rate, ramp_type)
        self.t_accel["feed"] = step_timings    
        self.n_accel["feed"] = len(step_timings)

    def get_motion_type(self):
        """Get motion type of stepper motor"""
        return self.motion_type

    def set_motion_type(self, motion_type):
        """Set motion type of stepper motor"""
        self.motion_type = motion_type

    def calc_steps(self, dist):
        self.logger.debug("Caluclating number of steps")
        n = int(round(abs(dist) * 360.0 / self.step_angle / self.travel_per_rev * self.mode))
        self.logger.debug("{} steps required to reach destination".format(n))
        return n
        
    def plan_line(self, dist):
        step_intervals = []
        n = self.calc_steps(dist)
#        self.logger.debug("Moving {}mm".format(dist))
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
    
    def plan_interpolated_line(self, dist):
        nx = self.calc_steps(dist["X"])
        ny = self.calc_steps(dist["Y"])
        nz = self.calc_steps(dist["Z"])
        n = []
        for ele in [nx, ny, nz]:
            if ele > 0:
                n.append(ele)
        step_intervals = []
        step_interval = 0.1
        delay = step_interval * 0.5
        xp = 0
        yp = 0
        zp = 0
        min_dist = min(n)
        ratio_x = float(nx) / min_dist
        ratio_y = float(ny) / min_dist
        ratio_z = float(nz) / min_dist
        for i in range(min_dist):
            steps_x = int(round(xp + ratio_x) - round(xp))
            steps_y = int(round(yp + ratio_y) - round(yp))
            steps_z = int(round(zp + ratio_z) - round(zp))

            xp += ratio_x
            yp += ratio_y
            zp += ratio_z

            for j in range(steps_x):
                step_intervals.append(("X", delay))
            for k in range(steps_y):
                step_intervals.append(("Y", delay))
            for m in range(steps_z):
                step_intervals.append(("Z", delay))

        return step_intervals
            
    
    def plan_interpolated_circle(self, x0, y0, r):
        #n = self.calc_steps(r)
        x = 0
        y = -r
        d = 1.25 - r
        points = []
        init_points = [(x, y)]
        dx = []
        dy = []
        # 3rd quadrant
        while x > y:
            if d < 0:
                x -= 1
                d += -2*x + 1
                
            else:
                x -= 1
                y += 1
                d += -2*(x-y) + 1
            point = (x, y)
            init_points.append(point)
        octant_len = len(init_points)
        for i in range(octant_len-2, -1, -1):
            point = (init_points[i][1], init_points[i][0])
            init_points.append(point)
        points.extend(init_points)
        # 2nd quadrant
        for p in init_points[1:]:
            points.append((p[1], -p[0]))
        # 1st quadrant
        for p in init_points[1:]:
            points.append((-p[0], -p[1]))
        # 4th quadrant
        for p in init_points[1:]:
            points.append((-p[1], p[0]))
            
        for i in range(1, len(points)):
            dx = points[i][0] - points[i-1][0]
            dy = points[i][1] - points[i-1][1]
            print(dx, dy)
            
    def configure_ramp(self, vm, method="trapezoidal"):
        if method == "trapezoidal":
            return (self._configure_ramp_trapezoidal(vm))
        elif method == "sigmoidal":
            return (self._configure_ramp_sigmoidal(vm))
        elif method == "polynomial":
            return (self._configure_ramp_polynomial(vm))

    def _configure_ramp_trapezoidal(self, vm):
        self.logger.info("Generating trapezoidal ramp profile [v_max={}]".format(vm))
#        outf = open("ramp_profile_t" + str(int(vm)) + ".csv", "w")
        sqrt = math.sqrt
        # steps per revolution: microstepping mode as factor
        spr = 360.0 / self.step_angle * self.mode
        # Number of steps it takes to move axis 1mm
        steps_per_mm = spr / self.travel_per_rev
        # linear movement along the axes per step
        # angle of rotation (phi) per step in rad: 2 * PI = 360 degrees
        # [rotation_angle = 2 * PI / SPR]
        angle = 2 * math.pi / spr
        # Convert target velocity from mm/min to rad/s
        w = vm / 60 * steps_per_mm * angle
        # Convert acceleration from mm/s^2 to rad/s^2
        a = self.accel * steps_per_mm * angle
        # Calculation of number of steps needed to accelerate/decelerate
        # vf = final velocity (rad/s)
        # a = acceleration (rad/s^2)
        # [n_steps = vf^2 / (2 * rotation_angle * a)]
        num_steps = int(round(w**2 / (2 * angle * a)))
        # Calculation of initial step duration during acceleration/deceleration ph\ase
        # [c0 = (f=1) * sqrt(2 * rotation_angle / a)]
        c0 = sqrt(2 * angle / a)
        # Add time intervals for steps to achieve linear acceleration
#        t = 0.0
        c = [c0]
#        cn = c0
        for i in range(1, num_steps):
            cn = c0 * (sqrt(i+1) - sqrt(i))
#            t += cn
#            outf.write("{};{}\n".format(t, 1.0/cn/40*60))
            c.append(cn)
        # Get the total duration of all acceleration steps
        # should be [t_a = cf/a]
        c_total = sum(c)
#        outf.close()
        return (c, c_total)

    def _configure_ramp_sigmoidal(self, vm):
        self.logger.info("Generating sigmoidal ramp profile [v_max={}]".format(vm))
#        outf = open("ramp_profile_s" + str(int(vm)) + ".csv", "w")
        # steps per revolution: microstepping mode as factor
        spr = 360.0 / self.step_angle * self.mode
        # Number of steps it takes to move axis 1mm
        steps_per_mm = spr / self.travel_per_rev
        # linear movement along the axes per step
        # angle of rotation (phi) per step in rad: 2 * PI = 360 degrees
        # [rotation_angle = 2 * PI / SPR]
        angle = 2 * math.pi / spr
        # Convert target velocity from mm/min to rad/s
        w = vm / 60 * steps_per_mm * angle
        # Convert acceleration from mm/s^2 to rad/s^2
        a = self.accel * steps_per_mm * angle
        ti = 0.4
        # pre-calculated values
        w_4_a = w / (4*a)
        a_4_w = (4*a) / w
        e_ti = math.e**(a_4_w*ti)
        e_n = math.e**(a_4_w*angle/w)
        t_mod = ti - w_4_a * math.log(0.005)
        
        num_steps = int(round(w**2 * (math.log(math.e**(a_4_w*t_mod) + e_ti) - math.log(e_ti + 1)) / (4*a*angle)))
#        t = 0.0
        c = []
        for i in range(1, num_steps):
            cn = w_4_a * math.log(((e_ti + 1) * e_n**(i+1) - e_ti)/((e_ti + 1) * e_n**i - e_ti))
#            t += cn
#            outf.write("{};{}\n".format(t, 1.0/cn/steps_per_mm*60))
            c.append(cn)
        # Get the total duration of all acceleration steps
        # should be [t_a = cf/a]
        c_total = sum(c)
#        outf.close()
        return (c, c_total)

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
        "sigmoidal",
        step_angle,
        travel_per_rev,
        mode,
        a,
        v,
        f,
        debug
    )
    #    mp.plan_interpolated_circle(20)
    dist = {"X": 10, "Y": 5, "Z": 2}
    intervals = mp.plan_interpolated_line(dist)
    print(intervals)
    #    mp.configure_ramp("scurve", v)


if __name__ == '__main__':
    main()
