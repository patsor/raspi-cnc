#!/usr/bin/env python

from argparse import ArgumentParser
import logging
import math

import config as cfg


def _mm_to_steps(value, step_angle, mode, lead):
    """Converts distance in millimeters to steps
    based on motor step angle, mode and lead of axis.
    """
    return int(round(value * mode * 360.0 / step_angle / lead))


def _mm_to_steps_ax(key, value):
    if key == "x":
        return _mm_to_steps(value, cfg.STEPPER_STEP_ANGLE_X, cfg.STEPPER_MODE_X, cfg.AXIS_LEAD_X)
    elif key == "y":
        return _mm_to_steps(value, cfg.STEPPER_STEP_ANGLE_Y, cfg.STEPPER_MODE_Y, cfg.AXIS_LEAD_Y)
    elif key == "z":
        return _mm_to_steps(value, cfg.STEPPER_STEP_ANGLE_Z, cfg.STEPPER_MODE_Z, cfg.AXIS_LEAD_Z)


def _mm_per_min_to_pps(value, step_angle, mode, lead):
    """Converts velocity in millimeters per minute to steps
    based on motor step angle, mode and lead of axis."""
    return value / lead / 60 * mode * 360 / step_angle


def _mm_per_min_to_pps_ax(key, value):
    if key == "x":
        return _mm_per_min_to_pps(value, cfg.STEPPER_STEP_ANGLE_X, cfg.STEPPER_MODE_X, cfg.AXIS_LEAD_X)
    elif key == "y":
        return _mm_per_min_to_pps(value, cfg.STEPPER_STEP_ANGLE_Y, cfg.STEPPER_MODE_Y, cfg.AXIS_LEAD_Y)
    elif key == "z":
        return _mm_per_min_to_pps(value, cfg.STEPPER_STEP_ANGLE_Z, cfg.STEPPER_MODE_Z, cfg.AXIS_LEAD_Z)


def _configure_ramp_trapezoidal(vm, mode, step_angle, lead, accel):
    """Generates pulses for trapezoidal ramp curve based on constant acceleration.

    Parameters:
        vm (float): Target velocity after acceleration phase
        mode (int): Stepper mode
        step_angle (float): Stepper step angle
        lead (int): Axis lead
        accel (float): Acceleration in mm/s^2

    Returns:
        c (list): Step timing intervals for each step during acceleration
    """

    pi = math.pi
    sqrt = math.sqrt
    # steps per revolution: microstepping mode as factor
    spr = 360.0 / step_angle * mode
    # Number of steps it takes to move axis 1mm
    steps_per_mm = spr / lead
    # linear movement along the axes per step
    # angle of rotation (phi) per step in rad: 2 * PI = 360 degrees
    # [rotation_angle = 2 * PI / SPR]
    angle = 2 * pi / spr
    # Convert target velocity from mm/min to rad/s
    w = vm / 60 * steps_per_mm * angle
    # Convert acceleration from mm/s^2 to rad/s^2
    a = accel * steps_per_mm * angle
    # Calculation of number of steps needed to accelerate/decelerate
    # vf = final velocity (rad/s)
    # a = acceleration (rad/s^2)
    # [n_steps = vf^2 / (2 * rotation_angle * a)]
    num_steps = int(round(w**2 / (2 * angle * a)))
    # Calculation of initial step duration during acceleration/deceleration ph\ase
    # [c0 = (f=1) * sqrt(2 * rotation_angle / a)]
    c0 = sqrt(2 * angle / a)
    # Add time intervals for steps to achieve linear acceleration
    c = [round(c0, 6)]
    for i in range(1, num_steps):
        cn = c0 * (sqrt(i+1) - sqrt(i))
        c.append(round(cn, 6))
    # Get the total duration of all acceleration steps
    # should be [t_a = cf/a]
    # c_total = sum(c)
    # return (c, c_total)
    return c


def _configure_ramp_sigmoidal(vm, mode, step_angle, lead, accel):
    """Generates pulses for sigmoidal ramp curve based on constant acceleration.

    Parameters:
        vm (float): Target velocity after acceleration phase
        mode (int): Stepper mode
        step_angle (float): Stepper step angle
        lead (int): Axis lead
        accel (float): Acceleration in mm/s^2

    Returns:
        c (list): Step timing intervals for each step during acceleration
    """
    if not vm:
        return None
    
    e = math.e
    log = math.log
    pi = math.pi
    # steps per revolution: microstepping mode as factor
    spr = 360.0 / step_angle * mode
    # Number of steps it takes to move axis 1mm
    steps_per_mm = spr / lead
    # linear movement along the axes per step
    # angle of rotation (phi) per step in rad: 2 * PI = 360 degrees
    # [rotation_angle = 2 * PI / SPR]
    angle = 2 * pi / spr
    # Convert target velocity from mm/min to rad/s
    w = vm / 60.0 * steps_per_mm * angle
    # Convert acceleration from mm/s^2 to rad/s^2
    a = accel * steps_per_mm * angle
    ti = 0.4
    # pre-calculated values
    w_4_a = w / (4*a)
    a_4_w = (4*a) / w
    e_ti = e**(a_4_w*ti)
    e_n = e**(a_4_w*angle/w)
    t_mod = ti - w_4_a * log(0.005)

    num_steps = int(round(
        w**2 * (log(e**(a_4_w*t_mod) + e_ti) - log(e_ti + 1)) / (4*a*angle)))

    c = []
    for i in range(1, num_steps):
        cn = w_4_a * \
            log(((e_ti + 1) * e_n**(i+1) - e_ti) /
                ((e_ti + 1) * e_n**i - e_ti))

        c.append(cn)
    # Get the total duration of all acceleration steps
    # should be [t_a = cf/a]
    # c_total = sum(c)
    # return (c, c_total)
    return c


def _configure_ramp_polynomial(vm, mode, step_angle, lead, accel):
    """Generates pulses for polynomial ramp curve based on constant acceleration.

    Parameters:
        vm (float): Target velocity after acceleration phase
        mode (int): Stepper mode
        step_angle (float): Stepper step angle
        lead (int): Axis lead
        accel (float): Acceleration in mm/s^2

    Returns:
        c (list): Step timing intervals for each step during acceleration
    """

    pi = math.pi
    sqrt = math.sqrt
    # steps per revolution: microstepping mode as factor
    spr = 360.0 / step_angle * mode
    # Number of steps it takes to move axis 1mm
    steps_per_mm = spr / lead
    # linear movement along the axes per step
    # angle of rotation (phi) per step in rad: 2 * PI = 360 degrees
    # [rotation_angle = 2 * PI / SPR]
    step_angle_in_rad = 2 * pi / spr
    # Convert target velocity from mm/min to rad/s
    v3 = vm / 60 * steps_per_mm * step_angle_in_rad
    # Convert acceleration from mm/s^2 to rad/s^2
    accel_in_rad = accel * steps_per_mm * step_angle_in_rad
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


def _overlay_ramp(steps, ramp, sign):
    intervals = []
    steps_2 = steps / 2
    ramp_size = len(ramp)
    for i in range(steps):
        if i < ramp_size and i < steps_2:
            intervals.append((sign, ramp[i]))
        elif i >= steps_2 and i >= steps - ramp_size:
            intervals.append((sign, ramp[steps-i-1]))
        else:
            intervals.append((sign, ramp[-1]))

    return intervals


def _plan_move(x, y, z, vx, vy, vz):
    """Generates pulses for rapid positioning movement.
    Returns tuples vector with pulse direction(1 | -1) and
    pulse duration for the motor.

    Parameters:
        x (int): X axis end point in steps
        y (int): Y axis end point in steps
        z (int): Z axis end point in steps
        vx (float): X axis velocity in [1/s]
        vy (float): Y axis velocity in [1/s]
        vz (float): Z axis velocity in [1/s]

    Returns:
        ix (list): Step timing intervals for X axis movement
        iy (list): Step timing intervals for Y axis movement
        iz (list): Step timing intervals for Z axis movement
    """

    ramp_x = _configure_ramp_sigmoidal(vx, cfg.STEPPER_MODE_X, cfg.STEPPER_STEP_ANGLE_X, cfg.AXIS_LEAD_X, cfg.AXIS_ACCELERATION_X)
    ramp_y = _configure_ramp_sigmoidal(vy, cfg.STEPPER_MODE_Y, cfg.STEPPER_STEP_ANGLE_Y, cfg.AXIS_LEAD_Y, cfg.AXIS_ACCELERATION_Y)
    ramp_z = _configure_ramp_sigmoidal(vz, cfg.STEPPER_MODE_Z, cfg.STEPPER_STEP_ANGLE_Z, cfg.AXIS_LEAD_Z, cfg.AXIS_ACCELERATION_Z)
    
    # Get signs of distance vector
    sign_x = 1 if x >= 0 else -1
    sign_y = 1 if y >= 0 else -1
    sign_z = 1 if z >= 0 else -1

    # Generate intervals for stepper based on velocity
    ix = _overlay_ramp(abs(x), ramp_x, sign_x)
    iy = _overlay_ramp(abs(y), ramp_y, sign_y)
    iz = _overlay_ramp(abs(z), ramp_z, sign_z)

    
    #ix = [(sign_x, 1 / vx)] * abs(x)
    #iy = [(sign_y, 1 / vy)] * abs(y)
    #iz = [(sign_z, 1 / vz)] * abs(z)

    return ix, iy, iz


def _plan_interpolated_line(x, y, vx, vy):
    """Generates pulses for linear interpolation movement.
    Returns tuples vector with pulse direction(1 | -1) and
    pulse duration for the motor.

    Parameters:
        x (int): X axis end point in steps
        y (int): Y axis end point in steps
        vx (float): X axis velocity in [1/s]
        vy (float): Y axis velocity in [1/s]

    Returns:
        ix (list): Step timing intervals for X axis movement
        iy (list): Step timing intervals for Y axis movement
    """

    # Get signs of distance vector
    sign_x = 1 if x >= 0 else -1
    sign_y = 1 if y >= 0 else -1

    # Generate intervals for stepper based on velocity
    ix = [(sign_x, 1.0 / vx)] * abs(x)
    iy = [(sign_y, 1.0 / vy)] * abs(y)

    return ix, iy


def _plan_interpolated_arc(r, x_start, y_start, x_end, y_end, vx, vy, is_cw=True):
    """Generates pulses for circular interpolation movement.
    Returns tuples vector with pulse direction(1 | -1) and
    pulse duration for the motor.

    Parameters:
        r (int): radius in steps
        x_start (int): First axis starting point in steps
        y_start (int): Second axis starting point in steps
        x_end (int): First axis end point in steps
        y_end (int): Second axis end point in steps
        vx (float): First axis velocity in [1/s]
        vy (float): Second axis velocity in [1/s]
        is_cw (bool): Is direction clockwise

    Returns:
        ix (list): Step timing intervals for X axis movement
        iy (list): Step timing intervals for Y axis movement
    """

    ix = []
    iy = []

    phi_x = 0
    phi_y = 0

    x = x_start
    y = y_start
    phi_x0 = 0
    phi_y0 = 0

    kx = 0
    ky = 0
    factor_x = 1
    factor_y = 1
    # print("Start")
    #print(r, x_start, y_start, x_end, y_end, is_cw)
    inv_factor = 1
    if not is_cw:
        inv_factor = -1
    else:
        inv_factor = 1
    # Precompute some values before loop to improve efficiency
    n = 4 * r    # total number of steps
    pi = math.pi
    pi_1_2 = pi / 2
    pi_3_2 = 3 * pi / 2
    pi_2 = 2 * pi
    acos = math.acos
    asin = math.asin
    r_vx = r / vx
    r_vy = r / vy
    initial = True
    for i in range(n):
        # first quadrant (0 <= phi < pi/2)
        # if 0 <= phi_x < pi_1_2:
        if x == 0 and y == 0:
            phi_x0 = 0
            phi_y0 = 0
        if x < r and y*inv_factor >= 0:
            kx = 0
            ky = 0
            factor_x = 1
            factor_y = 1
        # second quadrant (pi/2 <= phi < pi)
        # elif pi_1_2 <= phi_x < pi:
        elif x >= r and y*inv_factor > 0:
            kx = 0
            ky = 1
            factor_x = 1
            factor_y = -1
        # third quadrant (pi <= phi < 3*pi/2)
        # elif pi <= phi_x < pi_3_2:
        elif x > r and y*inv_factor <= 0:
            kx = 1
            ky = 1
            factor_x = -1
            factor_y = -1
        # fourth quadrant (3*pi/2 <= phi < pi_2)
        # elif pi_3_2 <= phi_x < pi_2:
        elif x <= r and y*inv_factor < 0:
            kx = 1
            ky = 2
            factor_x = -1
            factor_y = 1

        # negate y factor if counter-clockwise
        factor_y *= inv_factor
        # init phi values if not yet done
        if initial:
            phi_x0 = factor_x * acos(float(-x+r)/r) + pi * 2 * kx
            phi_y0 = factor_y * asin(float(y)/r) + pi * ky
            initial = False
        # if I and J is given, x and y will be asynchronous
        # in order to synchronize, only one of the two can be incremented
        x_dist = abs(x - r)
        y_dist = r - abs(y)
        xy_compare = inv_factor*(x_dist - y_dist)
        #print(x_dist, y_dist)
        # Depending on choice:
        # Calculate phi for the next steps on x and/or y axis
        # taken into account periodicity as we need full 360 degrees
        # Calculate delta t based on the following formulas:
        # Distance traveled on circular pathway:
        # delta_s = r * delta_phi
        # and the time required to do so
        # delta_t = delta_s / v
        # append interval to ix and/or iy

        if xy_compare < 0:
            x += factor_x
            phi_x = factor_x * acos(float(-x+r)/r) + pi * 2 * kx
            dtx = r_vx * (phi_x - phi_x0)
            ix.append((factor_x, dtx))
            phi_x0 = phi_x

        elif xy_compare > 0:
            y += factor_y
            phi_y = factor_y * asin(float(y)/r) + pi * ky
            dty = r_vy * (phi_y - phi_y0)
            iy.append((factor_y, dty))
            phi_y0 = phi_y
        else:
            x += factor_x
            phi_x = factor_x * acos(float(-x+r)/r) + pi * 2 * kx
            dtx = r_vx * (phi_x - phi_x0)
            ix.append((factor_x, dtx))
            phi_x0 = phi_x

            y += factor_y
            phi_y = factor_y * asin(float(y)/r) + pi * ky
            dty = r_vy * (phi_y - phi_y0)
            iy.append((factor_y, dty))
            phi_y0 = phi_y

        #print(i, x, y, phi_x*180/pi, phi_y*180/pi)

        # Exit loop if endpoint is reached
        if x_end or y_end:
            if (x == x_end and y == y_end):
                break

    return ix, iy


class MotionPlanner(object):
    """
    A class containing all methods for CNC motion planning.

    Attributes:
        logger (Logger): Logging object
        debug (bool): Enable debugging mode
    """

    def __init__(self, debug=False):
        self.logger = logging.getLogger("MotionPlanner")
        self._debug = debug

    def plan_move(self, ds, v):
        """Plans rapid positioning move.
        In this mode the axes move at max speed
        to the desired position. Shorter vectors finish first.

        Parameters:
            ds (tuple list): axis deltas in mm
            v (tuple list): axis velocities in mm/min

        Returns:
            ix (list): Step timing intervals for X axis movement
            iy (list): Step timing intervals for Y axis movement
            iz (list): Step timing intervals for Z axis movement
        """

        steps = []
        pps = []
        for key, val in ds:
            steps.append(_mm_to_steps_ax(key, val))
        for key, val in v:
            pps.append(_mm_per_min_to_pps_ax(key, val))

        return _plan_move(steps[0], steps[1], steps[2], pps[0], pps[1], pps[2])

    def plan_interpolated_line(self, ds, v):
        """Plans linear interpolation movement on specified plane.
        The axis movements will be synchronized using the defined
        feed rate. All vectors finish at the same time.

        Parameters:
            ds (tuple list): axis deltas in mm
            v (float): Feed rate of interpolated movement in mm/min

        Returns:
            ia (list): Step timing intervals for first planar axis movement
            ib (list): Step timing intervals for second planar axis movement
        """

        s = math.sqrt(ds[0][1]*ds[0][1] + ds[1][1]*ds[1][1])
        ti = s / v

        steps = []
        pps = []
        for key, val in ds:
            steps.append(_mm_to_steps_ax(key, val))
            pps.append(_mm_per_min_to_pps_ax(key, abs(val) / ti))

        return _plan_interpolated_line(steps[0], steps[1], pps[0], pps[1])

    def plan_interpolated_arc(self, r, ds, de, v, is_cw):
        """Plans circular interpolation movement on specified plane.
        The movement will be synchronized on selected plane till
        either a defined end point or the start of the
        circular movement is reached.

        Parameters:
            r (float): the radius of the arc
            ds (tuple list): axis starting points in mm
            de (tuple list): axis end points in mm
            v (float): Feed rate of interpolated movement
            is_cw (bool): Is direction clockwise

        Returns:
            ia (list): Step timing intervals for first planar axis movement
            ib (list): Step timing intervals for second planar axis movement
        """
        steps = []
        pps = []
        for key, val in ds:
            steps.append(_mm_to_steps_ax(key, val))
            pps.append(_mm_per_min_to_pps_ax(key, v))
        for key, val in de:
            steps.append(_mm_to_steps_ax(key, val))
        if steps[0] or steps[1]:
            steps_r = math.sqrt(steps[0]*steps[0]+steps[1]*steps[1])
        else:
            steps_r = _mm_to_steps_ax(ds[0][0], r)
        return _plan_interpolated_arc(steps_r, steps[0], steps[1], steps[2], steps[3], pps[0], pps[1], is_cw)
