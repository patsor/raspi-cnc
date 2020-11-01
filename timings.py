#!/usr/bin/env python

import timeit


def main():

    r = 5
    n = 1000

    t1 = timeit.repeat(
        "_plan_interpolated_line_bresenham(800, 400, 100, 100)",
        setup="from motion_planner import _plan_interpolated_line_bresenham",
        repeat=r,
        number=n
    )

    t2 = timeit.repeat(
        "_plan_interpolated_line_constant(800, 400, 100, 100)",
        setup="from motion_planner import _plan_interpolated_line_constant",
        repeat=r,
        number=n
    )

    t3 = timeit.repeat(
        "_plan_interpolated_circle_bresenham(400)",
        setup="from motion_planner import _plan_interpolated_circle_bresenham",
        repeat=r,
        number=n
    )

    t4 = timeit.repeat(
        "_plan_interpolated_arc(400, 0, 0, 100, 100)",
        setup="from motion_planner import _plan_interpolated_arc",
        repeat=r,
        number=n
    )

    print("Interpolated Line (Bresenham): {} loops, best of {}; {:.2f} usec per loop".format(
        n, r, min(t1) / n * 1000000))
    print("Interpolated Line (Constant): {} loops, best of {}; {:.2f} usec per loop".format(
        n, r, min(t2) / n * 1000000))
    print("Interpolated Circle (Bresenham): {} loops, best of {}; {:.2f} usec per loop".format(
        n, r, min(t3) / n * 1000000))
    print("Interpolated Circle (Constant): {} loops, best of {}; {:.2f} usec per loop".format(
        n, r, min(t4) / n * 1000000))


if __name__ == "__main__":
    main()
