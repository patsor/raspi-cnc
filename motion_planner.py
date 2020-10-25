#!/usr/bin/env python

import logging
from argparse import ArgumentParser

import config as cfg


def _transform_intervals(interval_list, factor=1):
    return [0 if ele == 1 or ele == -1 else 1 * factor for ele in interval_list]


def _calc_steps(dist, step_angle, mode, lead):
    return int(round(dist * 360.0 / step_angle / lead * mode))


def _plan_move(steps_x, steps_y, steps_z):

    factor_x = 1 if steps_x >= 0 else -1
    factor_y = 1 if steps_y >= 0 else -1
    factor_z = 1 if steps_z >= 0 else -1

    step_intervals_x = [factor_x] * abs(steps_x)
    step_intervals_y = [factor_y] * abs(steps_y)
    step_intervals_z = [factor_z] * abs(steps_z)

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
        # Compare the deviance to the slope
        # e(x) = f(x+1) - (y + 1)
        error = slope * (px + 1) - (py + 1)
        # if error >= 0.5
        if error >= 0.5 * slope:
            py += 1
            step_intervals_x.append(0)
            step_intervals_y.append(factor_y)
        # if error <= -0.5
        elif error <= -0.5:
            px += 1
            step_intervals_x.append(factor_x)
            step_intervals_y.append(0)
        # if error in between -0.5 and 0.5
        else:
            px += 1
            py += 1
            step_intervals_x.append(factor_x)
            step_intervals_y.append(factor_y)

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
    def __init__(self, ax, ay, az, debug=False):
        self.logger = logging.getLogger("MotionPlanner")
        self.ax = ax
        self.ay = ay
        self.az = az
        self.debug = debug

    def plan_move(self, x, y, z, sx, sy, sz):
        steps_x = _calc_steps(x, sx.step_angle, sx.mode, self.ax["lead"])
        steps_y = _calc_steps(y, sy.step_angle, sy.mode, self.ay["lead"])
        steps_z = _calc_steps(z, sz.step_angle, sz.mode, self.az["lead"])
        return _plan_move(steps_x, steps_y, steps_z)

    def plan_interpolated_line(self, x, y, sx, sy):
        steps_x = _calc_steps(x, sx.step_angle, sx.mode, self.ax["lead"])
        steps_y = _calc_steps(y, sy.step_angle, sy.mode, self.ay["lead"])
        return _plan_interpolated_line(steps_x, steps_y)

    def plan_interpolated_circle(self, r, sx, sy):
        steps_r = _calc_steps(r, sx.step_angle, sx.mode, self.ax["lead"])
        return _plan_interpolated_circle(steps_r)


def main():
    mp = MotionPlanner()
    mp._plan_interpolated_circle(5)


if __name__ == '__main__':
    main()
