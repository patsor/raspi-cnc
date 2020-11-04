#!/usr/bin/env python

import timeit


def main():

    r = 5
    n = 1000

    t1 = timeit.repeat(
        "_plan_interpolated_line(800, 400, 100, 100)",
        setup="from motion_planner import _plan_interpolated_line",
        repeat=r,
        number=n
    )

    t2 = timeit.repeat(
        "_plan_interpolated_arc(400, 0, 0, 0, 0, 100, 100)",
        setup="from motion_planner import _plan_interpolated_arc",
        repeat=r,
        number=n
    )

    print("Interpolated Line: {} loops, best of {}; {:.2f} usec per loop".format(
        n, r, min(t1) / n * 1000000))
    print("Interpolated Arc: {} loops, best of {}; {:.2f} usec per loop".format(
        n, r, min(t2) / n * 1000000))


if __name__ == "__main__":
    main()
