#!/usr/bin/env python

import math

def plan_interpolated_arc(r, to_x, to_y, vm, cw=True):
    # G02
    ix = []
    iy = []
    # Calculate max deviation from circle line
    e = 0.75
    #e = 10.0 / r
    print("Max. error: {}".format(e))
    # Calculate number of steps for a full circle
    n = int(round(2 * math.pi * r))
    # Calculate degree per step in radians
    phi = 2 * math.pi / n
    if cw:
        factor = -1
    else:
        factor = 1
    x0 = 0
    y0 = 0
    print(x0, y0, n)
    for i in range(1, n + 1):
        x = factor * r * math.cos(- factor * i * phi) - factor * r
        y = r * math.sin(i * phi)
        print(i, x, y)

        # Check if end point is reached
        if to_x or to_y:
            if x - e <= to_x <= x + e and y - e <= to_y <= y + e:
                break
        #if cw:
        #    if x  and to_x != 0 and y - to_y >= 0 and to_y != 0:
        #        break
        #else:
        #    if x - to_x <= 0 and to_x != 0 and y - to_y <= 0 and to_y != 0:
        #        break

        dx = x - x0
        dy = y - y0
        
        #print(dx, dy)
        if dx == 0.0:
            vx = 100.0
        else:
            vx = abs(dx * vm)
        if dy == 0.0:
            vy = 100.0
        else:
            vy = abs(dy * vm)
        tx = 1 / vx
        ty = 1 / vy

        if dx > 0:
            ix.append((1, tx))
        else:
            ix.append((-1, tx))

        if dy > 0:
            iy.append((1, ty))
        else:
            iy.append((-1, ty))
        
        x0 = x
        y0 = y
    return ix, iy

def main():
    print("Interpolated arc CW:")
    ix, iy = plan_interpolated_arc(150, 300, 0, 100, True)
    for i in range(len(ix)):
        print(i, ix[i], iy[i])



if __name__ == "__main__":
    main()