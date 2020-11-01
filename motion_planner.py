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
    tx = 1 / vx * abs(x)
    ty = 1 / vy * abs(y)

    return ix, iy


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


def _plan_interpolated_arc(r, to_x, to_y, vx, vy, cw=True):
    ix = []
    iy = []

    phi_x0 = 0
    phi_y0 = 0
    phi_x = 0
    phi_y = 0
    x = 0
    y = 0
    kx = 0
    ky = 0
    r_2 = 2 * r
    r_3 = 3 * r
    r_4 = 4 * r    # also total number of steps
    pi = math.pi
    acos = math.acos
    asin = math.asin
    r_vx = r / vx
    r_vy = r / vy
    for i in range(r_4):
        if 0 <= i < r:
            kx = 0
            ky = 0
            factor_x = 1
            factor_y = 1
        elif r <= i < r_2:
            kx = 0
            ky = 1
            factor_x = 1
            factor_y = -1
        elif r_2 <= i < r_3:
            kx = 1
            ky = 1
            factor_x = -1
            factor_y = -1
        elif r_3 <= i < r_4:
            kx = 1
            ky = 2
            factor_x = -1
            factor_y = 1

        x += factor_x
        y += factor_y
        phi_x = factor_x * acos(float(-x+r)/r) + pi * 2 * kx
        phi_y = factor_y * asin(float(y)/r) + pi * ky
        dtx = r_vx * (phi_x - phi_x0)
        dty = r_vy * (phi_y - phi_y0)
        phi_x0 = phi_x
        phi_y0 = phi_y
        ix.append((factor_x, dtx))
        iy.append((factor_y, dty))

        if to_x or to_y:
            if (x == to_x and y == to_y):
                break

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

        axv = self.ax["traversal_rate"]
        ayv = self.ay["traversal_rate"]
        azv = self.az["traversal_rate"]

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
            xy = math.sqrt(abs(x)**2 + abs(y)**2)
            ti = xy / feed_rate
            pps_x = _mm_per_min_to_pps(abs(x) / ti, sxa, sxm, axl)
            pps_y = _mm_per_min_to_pps(abs(y) / ti, sxa, sxm, axl)
            print(pps_x, pps_y)
            return _plan_interpolated_line_constant(steps_x, steps_y, pps_x, pps_y)
        elif plane == "XZ":
            xz = math.sqrt(abs(x)**2 + abs(z)**2)
            ti = xz / feed_rate
            pps_x = _mm_per_min_to_pps(abs(x) / ti, sxa, sxm, axl)
            pps_z = _mm_per_min_to_pps(abs(z) / ti, sza, szm, azl)
            return _plan_interpolated_line_constant(steps_x, steps_z, pps_x, pps_z)
        elif plane == "YZ":
            yz = math.sqrt(abs(y)**2 + abs(z)**2)
            ti = yz / feed_rate
            pps_y = _mm_per_min_to_pps(abs(y) / ti, sya, sym, ayl)
            pps_z = _mm_per_min_to_pps(abs(z) / ti, sza, szm, azl)
            return _plan_interpolated_line_constant(steps_y, steps_z, pps_y, pps_z)
        else:
            return None

    def plan_interpolated_arc(self, r, x, y, feed_rate, cw, plane="XY"):
        sxa = self.sx.step_angle
        sya = self.sy.step_angle
        sza = self.sz.step_angle

        sxm = self.sx.mode
        sym = self.sy.mode
        szm = self.sz.mode

        axl = self.ax["lead"]
        ayl = self.ay["lead"]
        azl = self.az["lead"]

        steps_r = _mm_to_steps(r, sxa, sxm, axl)
        steps_x = _mm_to_steps(x, sxa, sxm, axl)
        steps_y = _mm_to_steps(y, sya, sym, ayl)
        #steps_z = _mm_to_steps(z, sza, szm, azl)

        if plane == "XY":
            pps_x = _mm_per_min_to_pps(feed_rate, sxa, sxm, axl)
            pps_y = _mm_per_min_to_pps(feed_rate, sya, sym, ayl)
            print(steps_r, pps_x, pps_y)
            return _plan_interpolated_arc(steps_r, steps_x, steps_y, pps_x, pps_y, cw)
        elif plane == "XZ":
            pps_x = _mm_per_min_to_pps(feed_rate, sxa, sxm, axl)
            pps_z = _mm_per_min_to_pps(feed_rate, sza, szm, azl)
            return _plan_interpolated_arc(steps_r, steps_x, steps_y, pps_x, pps_z, cw)
        elif plane == "YZ":
            pps_y = _mm_per_min_to_pps(feed_rate, sya, sym, ayl)
            pps_z = _mm_per_min_to_pps(feed_rate, sza, szm, azl)
            return _plan_interpolated_arc(steps_r, steps_x, steps_y, pps_y, pps_z, cw)
        else:
            return None


def main():
    mp = MotionPlanner()
    mp._plan_interpolated_circle(5)


if __name__ == "__main__":
    main()
