#!/usr/bin/env python

import time
import math
import logging
from argparse import ArgumentParser

import config as cfg


def _transform_intervals(interval_list, factor=1):
    return [0 if ele == 1 or ele == -1 else 1 * factor for ele in interval_list]


def _calc_steps(dist, step_angle, mode, travel_per_rev):
    return int(round(abs(dist) * 360.0 / step_angle / travel_per_rev * mode))


def _plan_move(steps_x, steps_y, steps_z):
    step_intervals_x = []
    step_intervals_y = []
    step_intervals_z = []

    factor_x = 1 if steps_x >= 0 else -1
    factor_y = 1 if steps_y >= 0 else -1
    factor_z = 1 if steps_z >= 0 else -1

    x = abs(steps_x)
    y = abs(steps_y)
    z = abs(steps_z)

    max_steps = max(x, y, z)

    for i in range(max_steps):
        if i < x:
            step_intervals_x.append(factor_x)
        else:
            step_intervals_x.append(0)
        if i < y:
            step_intervals_y.append(factor_y)
        else:
            step_intervals_y.append(0)
        if i < z:
            step_intervals_z.append(factor_z)
        else:
            step_intervals_z.append(0)

    return step_intervals_x, step_intervals_y, step_intervals_z


def _plan_interpolated_line(steps_x, steps_y):

    step_intervals_x = []
    step_intervals_y = []

    factor_x = 1 if steps_x >= 0 else -1
    factor_y = 1 if steps_y >= 0 else -1

    x = abs(steps_x)
    y = abs(steps_y)

    slope = float(y) / x

    px = 0
    py = 0

    while px != x or py != y:
        # if (f(x+1) - y) >= 1, y + 1
        # else x + 1
        if (slope * (px + 1) - py >= 1):
            py += 1
            step_intervals_x.append(0)
            step_intervals_y.append(factor_y)
        else:
            px += 1
            step_intervals_x.append(factor_x)
            step_intervals_y.append(0)

    return step_intervals_x, step_intervals_y


def _plan_interpolated_circle(r):
    step_intervals_x = []
    step_intervals_y = []
    q2_intervals_x = []
    q2_intervals_y = []
    px = 0
    py = 0

    while px != r or py != r:

        px_inc = px + 1
        py_inc = py + 1
        # Calculate quadratic error on x axis for next step in x direction
        # Formula: e = r^2 - ((r - xn+1)^2 + yn^2)
        ex = abs(px_inc * (2 * r - px_inc) - py * py)
        # Calculate quadratic error on y axis for next step in y direction
        # Formula: e = r^2 - ((r - xn)^2 + yn+1^2)
        ey = abs(px * (2 * r - px) - py_inc * py_inc)

        # Compare errors and choose path with least quadratic error
        if ex < ey:
            px += 1
            q2_intervals_x.append(1)
            q2_intervals_y.append(0)
        else:
            py += 1
            q2_intervals_x.append(0)
            q2_intervals_y.append(1)

    q1_intervals_x = _transform_intervals(q2_intervals_x)
    q4_intervals_x = _transform_intervals(q1_intervals_x, -1)
    q3_intervals_x = _transform_intervals(q2_intervals_x, -1)

    q1_intervals_y = _transform_intervals(q2_intervals_y, -1)
    q4_intervals_y = _transform_intervals(q1_intervals_y, -1)
    q3_intervals_y = _transform_intervals(q2_intervals_y)

    step_intervals_x.extend(q2_intervals_x)
    step_intervals_x.extend(q1_intervals_x)
    step_intervals_x.extend(q4_intervals_x)
    step_intervals_x.extend(q3_intervals_x)

    step_intervals_y.extend(q2_intervals_y)
    step_intervals_y.extend(q1_intervals_y)
    step_intervals_y.extend(q4_intervals_y)
    step_intervals_y.extend(q3_intervals_y)

    return step_intervals_x, step_intervals_y


class MotionPlanner(object):
    def __init__(self, debug=False):
        self.logger = logging.getLogger("MotionPlanner")
        self.debug = debug

        #self.t_accel = {}
        #self.n_accel = {}

        # (step_timings, c_total) = self.configure_ramp(
        #    cfg.max_traverse_rate, cfg.ramp_type)
        #self.t_accel["traverse"] = step_timings
        #self.n_accel["traverse"] = len(step_timings)

        # (step_timings, c_total) = self.configure_ramp(
        #    cfg.max_feed_rate, step_angle, mode, travel_per_rev, acceleration_rate, cfg.ramp_type)
        #self.t_accel["feed"] = step_timings
        #self.n_accel["feed"] = len(step_timings)

    def get_motion_type(self):
        """Get motion type of stepper motor"""
        return self.motion_type

    def set_motion_type(self, motion_type):
        """Set motion type of stepper motor"""
        self.motion_type = motion_type

    def plan_move(self, x, y, z, sx, sy, sz):
        steps_x = _calc_steps(x, sx.step_angle, sx.mode, sx.travel_per_rev)
        steps_y = _calc_steps(y, sy.step_angle, sy.mode, sy.travel_per_rev)
        steps_z = _calc_steps(z, sz.step_angle, sz.mode, sz.travel_per_rev)
        return _plan_move(steps_x, steps_y, steps_z)

    def plan_interpolated_line(self, x, y, sx, sy):
        steps_x = _calc_steps(x, sx.step_angle, sx.mode, sx.travel_per_rev)
        steps_y = _calc_steps(y, sy.step_angle, sy.mode, sy.travel_per_rev)
        return _plan_interpolated_line(steps_x, steps_y)

    def plan_interpolated_circle(self, r, sx, sy):
        steps_r = _calc_steps(r, sx.step_angle, sx.mode, sx.travel_per_rev)
        return _plan_interpolated_circle(steps_r)

    def configure_ramp(self, vm, step_angle, mode, travel_per_rev, acceleration_rate, method="trapezoidal"):
        if method == "trapezoidal":
            return (self._configure_ramp_trapezoidal(vm, step_angle, mode, travel_per_rev, acceleration_rate))
        elif method == "sigmoidal":
            return (self._configure_ramp_sigmoidal(vm, step_angle, mode, travel_per_rev, acceleration_rate))
        elif method == "polynomial":
            return (self._configure_ramp_polynomial(vm, step_angle, mode, travel_per_rev, acceleration_rate))

    def _configure_ramp_trapezoidal(self, vm, step_angle, mode, travel_per_rev, acceleration_rate):
        self.logger.info(
            "Generating trapezoidal ramp profile [v_max={}]".format(vm))
#        outf = open("ramp_profile_t" + str(int(vm)) + ".csv", "w")
        sqrt = math.sqrt
        # steps per revolution: microstepping mode as factor
        spr = 360.0 / step_angle * mode
        # Number of steps it takes to move axis 1mm
        steps_per_mm = spr / travel_per_rev
        # linear movement along the axes per step
        # angle of rotation (phi) per step in rad: 2 * PI = 360 degrees
        # [rotation_angle = 2 * PI / SPR]
        angle = 2 * math.pi / spr
        # Convert target velocity from mm/min to rad/s
        w = vm / 60 * steps_per_mm * angle
        # Convert acceleration from mm/s^2 to rad/s^2
        a = acceleration_rate * steps_per_mm * angle
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

    def _configure_ramp_sigmoidal(self, vm, step_angle, mode, travel_per_rev, acceleration_rate):
        self.logger.info(
            "Generating sigmoidal ramp profile [v_max={}]".format(vm))
#        outf = open("ramp_profile_s" + str(int(vm)) + ".csv", "w")
        # steps per revolution: microstepping mode as factor
        spr = 360.0 / step_angle * mode
        # Number of steps it takes to move axis 1mm
        steps_per_mm = spr / travel_per_rev
        # linear movement along the axes per step
        # angle of rotation (phi) per step in rad: 2 * PI = 360 degrees
        # [rotation_angle = 2 * PI / SPR]
        angle = 2 * math.pi / spr
        # Convert target velocity from mm/min to rad/s
        w = vm / 60 * steps_per_mm * angle
        # Convert acceleration from mm/s^2 to rad/s^2
        a = acceleration_rate * steps_per_mm * angle
        ti = 0.4
        # pre-calculated values
        w_4_a = w / (4*a)
        a_4_w = (4*a) / w
        e_ti = math.e**(a_4_w*ti)
        e_n = math.e**(a_4_w*angle/w)
        t_mod = ti - w_4_a * math.log(0.005)

        num_steps = int(round(
            w**2 * (math.log(math.e**(a_4_w*t_mod) + e_ti) - math.log(e_ti + 1)) / (4*a*angle)))
#        t = 0.0
        c = []
        for i in range(1, num_steps):
            cn = w_4_a * \
                math.log(((e_ti + 1) * e_n**(i+1) - e_ti) /
                         ((e_ti + 1) * e_n**i - e_ti))
#            t += cn
#            outf.write("{};{}\n".format(t, 1.0/cn/steps_per_mm*60))
            c.append(cn)
        # Get the total duration of all acceleration steps
        # should be [t_a = cf/a]
        c_total = sum(c)
#        outf.close()
        return (c, c_total)

    def _configure_ramp_polynomial(self, vm, step_angle, mode, travel_per_rev, acceleration_rate):
        sqrt = math.sqrt
        # steps per revolution: microstepping mode as factor
        spr = 360.0 / step_angle * mode
        # Number of steps it takes to move axis 1mm
        steps_per_mm = spr / travel_per_rev
        # linear movement along the axes per step
        # angle of rotation (phi) per step in rad: 2 * PI = 360 degrees
        # [rotation_angle = 2 * PI / SPR]
        step_angle_in_rad = 2 * math.pi / spr
        # Convert target velocity from mm/min to rad/s
        v3 = vm / 60 * steps_per_mm * step_angle_in_rad
        # Convert acceleration from mm/s^2 to rad/s^2
        accel_in_rad = acceleration_rate * steps_per_mm * step_angle_in_rad
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
    mp = MotionPlanner()
    mp._plan_interpolated_circle(5)


if __name__ == '__main__':
    main()
