#!/usr/bin/env python

import timeit

from motion_planner import _plan_interpolated_circle
from motion_planner import _plan_interpolated_circle_bresenham


def main():

    r = 5
    n = 1000

    t1 = timeit.repeat(
        "_plan_interpolated_line(800, 400)",
        setup="from motion_planner import _plan_interpolated_line",
        repeat=r,
        number=n
    )

    t2 = timeit.repeat(
        "_plan_interpolated_line_bresenham(800, 400)",
        setup="from motion_planner import _plan_interpolated_line_bresenham",
        repeat=r,
        number=n
    )

    t3 = timeit.repeat(
        "_plan_interpolated_circle(400)",
        setup="from motion_planner import _plan_interpolated_circle",
        repeat=r,
        number=n
    )

    t4 = timeit.repeat(
        "_plan_interpolated_circle_bresenham(400)",
        setup="from motion_planner import _plan_interpolated_circle_bresenham",
        repeat=r,
        number=n
    )

    t5 = timeit.repeat(
        "_plan_interpolated_circle_midpoint(400)",
        setup="from motion_planner import _plan_interpolated_circle_midpoint",
        repeat=r,
        number=n
    )

    print("Interpolated Line (Brute Force): {} loops, best of {}; {:.2f} usec per loop".format(
        n, r, min(t1) / n * 1000000))
    print("Interpolated Line (Bresenham): {} loops, best of {}; {:.2f} usec per loop".format(
        n, r, min(t2) / n * 1000000))

    print("Interpolated Circle (Brute Force): {} loops, best of {}; {:.2f} usec per loop".format(
        n, r, min(t3) / n * 1000000))
    print("Interpolated Circle (Bresenham): {} loops, best of {}; {:.2f} usec per loop".format(
        n, r, min(t4) / n * 1000000))
    print("Interpolated Circle (Midpoint): {} loops, best of {}; {:.2f} usec per loop".format(
        n, r, min(t5) / n * 1000000))


if __name__ == "__main__":
    main()
