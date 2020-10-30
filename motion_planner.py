#!/usr/bin/env python

from argparse import ArgumentParser
import logging
import math

import config as cfg


def _transform_intervals(interval_list, factor=1):
    return [0 if ele == 1 or ele == -1 else 1 * factor for ele in interval_list]


def _mm_to_steps(value, step_angle, mode, lead):
    return int(round(value * mode * 360.0 / step_angle / lead))


def _mm_per_min_to_pps(value, step_angle, mode, lead):
    return value / lead / 60 * mode * 360 / step_angle


def _plan_move(x, y, z, vx, vy, vz):

    # Get signs of distance vector
    sign_x = 1 if x >= 0 else -1
    sign_y = 1 if y >= 0 else -1
    sign_z = 1 if z >= 0 else -1

    # Generate intervals for stepper based on velocity
    ix = [(sign_x, 1 / vx)] * abs(x)
    iy = [(sign_y, 1 / vy)] * abs(y)
    iz = [(sign_z, 1 / vz)] * abs(z)

    return ix, iy, iz


def _plan_interpolated_line_bresenham(x, y, vx, vy):
    px = abs(x)
    py = abs(y)
    if py > px:
        iy, ix = _plan_interpolated_line_bresenham(y, x, vy, vx)
        return ix, iy

    ix = []
    iy = []

    sign_x = 1 if x >= 0 else -1
    sign_y = 1 if y >= 0 else -1

    d = 2*py - px

    for i in range(px):
        if d > 0:
            d -= 2 * px
            ix.append((sign_x, 1 / vx))
            iy.append((sign_y, 1 / vy))
        else:
            ix.append((sign_x, 1 / vx))
            iy.append((0, 1 / vy))
        d += 2 * py

    return ix, iy


def _plan_interpolated_line_constant(x, y, vx, vy):
    sign_x = 1 if x >= 0 else -1
    sign_y = 1 if y >= 0 else -1

    ix = [(sign_x, 1 / vx)] * abs(x)
    iy = [(sign_y, 1 / vy)] * abs(y)

    return ix, iy


def _plan_interpolated_circle_midpoint(r):
    step_intervals_x = []
    step_intervals_y = []

    points = []
    p1 = []
    p2 = []
    p3 = []
    p4 = []
    p5 = []
    p6 = []
    p7 = []
    p8 = []

    # Calculate first octant (x,y) using Bresenham algorithm

    px = r
    py = 0

    p = 1 - r

    while px > py:
        p1.append((-px, py))
        p2.append((-py, px))
        p3.append((py, px))
        p4.append((px, py))
        p5.append((px, -py))
        p6.append((py, -px))
        p7.append((-py, -px))
        p8.append((-px, -py))

        py += 1

        if p <= 0:
            p += 2 * py + 1
        else:
            px -= 1
            p += 2 * py - 2 * px + 1

    points.extend(p1)
    points.extend(p2[::-1])
    points.extend(p3)
    points.extend(p4[::-1])
    points.extend(p5)
    points.extend(p6[::-1])
    points.extend(p7)
    points.extend(p8[::-1])

    last_x = points[0][0]
    last_y = points[0][1]
    for x, y in points:
        if x != last_x or y != last_y:
            step_intervals_x.append(x - last_x)
            step_intervals_y.append(y - last_y)
        last_x = x
        last_y = y

    return step_intervals_x, step_intervals_y


def _plan_interpolated_circle_bresenham(r):
    ix = []
    iy = []

    points = []
    p1 = []
    p2 = []
    p3 = []
    p4 = []
    p5 = []
    p6 = []
    p7 = []
    p8 = []

    # Calculate first octant (x,y) using Bresenham algorithm
    px = 0
    py = r

    d = 3 - 2 * r

    while py >= px:
        p1.append((-py, px))
        p2.append((-px, py))
        p3.append((px, py))
        p4.append((py, px))
        p5.append((py, -px))
        p6.append((px, -py))
        p7.append((-px, -py))
        p8.append((-py, -px))

        px += 1

        if d > 0:
            py -= 1
            d += 4 * (px - py) + 10
        else:
            d += 4 * px + 6

    points.extend(p1)
    points.extend(p2[::-1])
    points.extend(p3)
    points.extend(p4[::-1])
    points.extend(p5)
    points.extend(p6[::-1])
    points.extend(p7)
    points.extend(p8[::-1])

    last_x = points[0][0]
    last_y = points[0][1]
    for x, y in points:
        if x != last_x or y != last_y:
            ix.append(x - last_x)
            iy.append(y - last_y)
        last_x = x
        last_y = y

    return ix, iy


def _plan_interpolated_circle_constant(r, vx):
    ix = []
    iy = []
    y_last = 0
    for x in range(1, (r * 2) + 1):
        y = math.sqrt(r**2 - (x - r)**2)
        vy = (y - y_last) * vx
        sign_y = 1 if vy >= 1 else -1
        y_last = y
        ix.append((1, 1 / vx))
        iy.append((sign_y, abs(1 / vy)))
        print(x, y, abs(1 / vy))

    neg_ix = [(-x, c) for x, c in ix]
    neg_iy = [(-y, c) for y, c in iy]

    ix.extend(neg_ix)
    iy.extend(neg_iy)
    print(ix)
    print(iy)
    return ix, iy


class MotionPlanner(object):
    def __init__(self, ax, ay, az, sx, sy, sz, debug=False):
        self.logger = logging.getLogger("MotionPlanner")
        self.ax = ax
        self.ay = ay
        self.az = az
        self.sx = sx
        self.sy = sy
        self.sz = sz
        self.debug = debug

    def plan_move(self, x, y, z):
        sxa = self.sx.step_angle
        sya = self.sy.step_angle
        sza = self.sz.step_angle

        sxm = self.sx.mode
        sym = self.sy.mode
        szm = self.sz.mode

        axl = self.ax["lead"]
        ayl = self.ay["lead"]
        azl = self.az["lead"]

        axv = self.ax["traversal_speed"]
        ayv = self.ay["traversal_speed"]
        azv = self.az["traversal_speed"]

        steps_x = _mm_to_steps(x, sxa, sxm, axl)
        steps_y = _mm_to_steps(y, sya, sym, ayl)
        steps_z = _mm_to_steps(z, sza, szm, azl)
        pps_x = _mm_per_min_to_pps(axv, sxa, sxm, axl)
        pps_y = _mm_per_min_to_pps(ayv, sya, sym, ayl)
        pps_z = _mm_per_min_to_pps(azv, sza, szm, azl)
        return _plan_move(steps_x, steps_y, steps_z, pps_x, pps_y, pps_z)

    def plan_interpolated_line(self, x, y, z, feed_rate, plane="XY"):
        sxa = self.sx.step_angle
        sya = self.sy.step_angle
        sza = self.sz.step_angle

        sxm = self.sx.mode
        sym = self.sy.mode
        szm = self.sz.mode

        axl = self.ax["lead"]
        ayl = self.ay["lead"]
        azl = self.az["lead"]

        steps_x = _mm_to_steps(x, sxa, sxm, axl)
        steps_y = _mm_to_steps(y, sya, sym, ayl)
        steps_z = _mm_to_steps(z, sza, szm, azl)

        if plane == "XY":
            xy = math.sqrt(abs(x)**2, abs(y)**2)
            ti = xy / feed_rate
            pps_x = _mm_per_min_to_pps(ti / x, sxa, sxm, axl)
            pps_y = _mm_per_min_to_pps(ti / y, sxa, sxm, axl)
            return _plan_interpolated_line_constant(steps_x, steps_y, pps_x, pps_y)
        elif plane == "XZ":
            xz = math.sqrt(abs(x)**2, abs(z)**2)
            ti = xz / feed_rate
            pps_x = _mm_per_min_to_pps(ti / x, sxa, sxm, axl)
            pps_z = _mm_per_min_to_pps(ti / z, sza, szm, azl)
            return _plan_interpolated_line_constant(steps_x, steps_z, pps_x, pps_z)
        elif plane == "YZ":
            yz = math.sqrt(abs(y)**2, abs(z)**2)
            ti = yz / feed_rate
            pps_y = _mm_per_min_to_pps(ti / y, sya, sym, ayl)
            pps_z = _mm_per_min_to_pps(ti / z, sza, szm, azl)
            return _plan_interpolated_line_constant(steps_y, steps_z, pps_y, pps_z)
        else:
            return None

    def plan_interpolated_circle(self, r, plane="XY"):
        sxa = self.sx.step_angle
        sya = self.sy.step_angle
        sza = self.sz.step_angle

        sxm = self.sx.mode
        sym = self.sy.mode
        szm = self.sz.mode

        steps_r = _mm_to_steps(r, sxa, sxm, axl)

        if plane == "XY":
            return _plan_interpolated_circle_midnight(steps_r)
        else:
            return None


def main():
    mp = MotionPlanner()
    mp._plan_interpolated_circle(5)


if __name__ == '__main__':
    main()
