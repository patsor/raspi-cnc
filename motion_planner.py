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


def _mm_per_min_to_pps(value, step_angle, mode, lead):
    """Converts velocity in millimeters per minute to steps 
    based on motor step angle, mode and lead of axis."""
    return value / lead / 60 * mode * 360 / step_angle


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
    w = vm / 60 * steps_per_mm * angle
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

    # Get signs of distance vector
    sign_x = 1 if x >= 0 else -1
    sign_y = 1 if y >= 0 else -1
    sign_z = 1 if z >= 0 else -1

    # Generate intervals for stepper based on velocity
    ix = [(sign_x, 1 / vx)] * abs(x)
    iy = [(sign_y, 1 / vy)] * abs(y)
    iz = [(sign_z, 1 / vz)] * abs(z)

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
    ix = [(sign_x, 1 / vx)] * abs(x)
    iy = [(sign_y, 1 / vy)] * abs(y)

    return ix, iy


def _plan_interpolated_arc(r, to_x, to_y, vx, vy, is_cw=True):
    """Generates pulses for circular interpolation movement.
    Returns tuples vector with pulse direction(1 | -1) and
    pulse duration for the motor.

    Parameters:
        r (int): radius in steps
        to_x (int): X axis end point in steps
        to_y (int): Y axis end point in steps
        vx (float): X axis velocity in [1/s]
        vy (float): Y axis velocity in [1/s]
        is_cw (bool): Is direction clockwise

    Returns:
        ix (list): Step timing intervals for X axis movement
        iy (list): Step timing intervals for Y axis movement
    """

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
    for i in range(n):
        # first quadrant (0 <= phi < pi/2)
        if 0 <= phi_x < pi_1_2:
            kx = 0
            ky = 0
            factor_x = 1
            factor_y = 1
        # second quadrant (pi/2 <= phi < pi)
        elif pi_1_2 <= phi_x < pi:
            kx = 0
            ky = 1
            factor_x = 1
            factor_y = -1
        # third quadrant (pi <= phi < 3*pi/2)
        elif pi <= phi_x < pi_3_2:
            kx = 1
            ky = 1
            factor_x = -1
            factor_y = -1
        # fourth quadrant (3*pi/2 <= phi < pi_2)
        elif pi_3_2 <= phi_x < pi_2:
            kx = 1
            ky = 2
            factor_x = -1
            factor_y = 1

        # negate y factor if counter-clockwise
        if not is_cw:
            factor_y *= -1

        x += factor_x
        y += factor_y
        # Calculate phi for the next steps on the x, y axis
        # taken into account periodicity as we need full 360 degrees
        phi_x = factor_x * acos(float(-x+r)/r) + pi * 2 * kx
        phi_y = factor_y * asin(float(y)/r) + pi * ky
        # Calculate delta t based on the following formulas:
        # Distance traveled on circular pathway:
        # delta_s = r * delta_phi
        # and the time required to do so
        # delta_t = delta_s / v
        dtx = r_vx * (phi_x - phi_x0)
        dty = r_vy * (phi_y - phi_y0)
        phi_x0 = phi_x
        phi_y0 = phi_y
        ix.append((factor_x, dtx))
        iy.append((factor_y, dty))

        # Exit loop if endpoint is reached
        if to_x or to_y:
            if (x == to_x and y == to_y):
                break

    return ix, iy


class MotionPlanner(object):
    """
    A class containing all methods for CNC motion planning.

    Attributes
    ----------
    logger: Logger
        Logging object
    sx: Stepper
        X axis stepper
    sy: Stepper
        Y axis stepper
    sz: Stepper
        Z axis stepper
    """

    def __init__(self, sx, sy, sz, debug=False):
        self.logger = logging.getLogger("MotionPlanner")
        self._sx = sx
        self._sy = sy
        self._sz = sz
        self._debug = debug

    def plan_move(self, x, y, z):
        """Plans rapid positioning move.
        In this mode the axes move at max speed
        to the desired position. Shorter vectors finish first.

        Parameters:
            x (float): X axis end point of the arc
            y (float): Y axis end point of the arc
            z (float): Z axis end point of the arc

        Returns:
            ix (list): Step timing intervals for X axis movement
            iy (list): Step timing intervals for Y axis movement
            iz (list): Step timing intervals for Z axis movement
        """

        sxa = cfg.STEPPER_X_STEP_ANGLE
        sya = cfg.STEPPER_Y_STEP_ANGLE
        sza = cfg.STEPPER_Z_STEP_ANGLE

        sxm = self._sx.get_mode()
        sym = self._sy.get_mode()
        szm = self._sz.get_mode()

        axl = cfg.AXIS_LEAD_X
        ayl = cfg.AXIS_LEAD_Y
        azl = cfg.AXIS_LEAD_Z

        axv = cfg.AXIS_TRAVERSAL_MM_PER_MIN_X
        ayv = cfg.AXIS_TRAVERSAL_MM_PER_MIN_Y
        azv = cfg.AXIS_TRAVERSAL_MM_PER_MIN_Z

        steps_x = _mm_to_steps(x, sxa, sxm, axl)
        steps_y = _mm_to_steps(y, sya, sym, ayl)
        steps_z = _mm_to_steps(z, sza, szm, azl)
        pps_x = _mm_per_min_to_pps(axv, sxa, sxm, axl)
        pps_y = _mm_per_min_to_pps(ayv, sya, sym, ayl)
        pps_z = _mm_per_min_to_pps(azv, sza, szm, azl)
        return _plan_move(steps_x, steps_y, steps_z, pps_x, pps_y, pps_z)

    def plan_interpolated_line(self, x, y, z, feed_rate, plane="XY"):
        """Plans linear interpolation movement on specified plane.
        The axis movements will be synchronized using the defined
        feed rate. All vectors finish at the same time.

        Parameters:
            x (float): X axis end point of the arc
            y (float): Y axis end point of the arc
            z (float): Z axis end point of the arc
            feed_rate (float): Feed rate of interpolated movement
            plane (str): Plane for the movement(XY, XZ or YZ)

        Returns:
            ix (list): Step timing intervals for X axis movement (only for planes: XY, XZ)
            iy (list): Step timing intervals for Y axis movement (only for planes: XY, YZ)
            iz (list): Step timing intervals for Z axis movement (only for planes: XZ, YZ)
        """

        sxa = cfg.STEPPER_X_STEP_ANGLE
        sya = cfg.STEPPER_Y_STEP_ANGLE
        sza = cfg.STEPPER_Z_STEP_ANGLE

        sxm = self._sx.get_mode()
        sym = self._sy.get_mode()
        szm = self._sz.get_mode()

        axl = cfg.AXIS_LEAD_X
        ayl = cfg.AXIS_LEAD_Y
        azl = cfg.AXIS_LEAD_Z

        steps_x = _mm_to_steps(x, sxa, sxm, axl)
        steps_y = _mm_to_steps(y, sya, sym, ayl)
        steps_z = _mm_to_steps(z, sza, szm, azl)

        if plane == "XY":
            xy = math.sqrt(abs(x)**2 + abs(y)**2)
            ti = xy / feed_rate
            pps_x = _mm_per_min_to_pps(abs(x) / ti, sxa, sxm, axl)
            pps_y = _mm_per_min_to_pps(abs(y) / ti, sxa, sxm, axl)
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

    def plan_interpolated_arc(self, r, x, y, feed_rate, is_cw, plane="XY"):
        """Plans circular interpolation movement on specified plane.
        The movement will be synchronized on selected plane till
        either a defined end point or the start of the
        circular movement is reached.

        Parameters:
            r (float): the radius of the arc
            x (float): X axis end point of the arc
            y (float): Y axis end point of the arc
            feed_rate (float): Feed rate of interpolated movement
            is_cw (bool): Is direction clockwise
            plane (str): Plane for the movement(XY, XZ or YZ)

        Returns:
            ix (list): Step timing intervals for X axis movement (only for planes: XY, XZ)
            iy (list): Step timing intervals for Y axis movement (only for planes: XY, YZ)
            iz (list): Step timing intervals for Z axis movement (only for planes: XZ, YZ)
        """

        sxa = cfg.STEPPER_X_STEP_ANGLE
        sya = cfg.STEPPER_Y_STEP_ANGLE
        sza = cfg.STEPPER_Z_STEP_ANGLE

        sxm = self._sx.get_mode()
        sym = self._sy.get_mode()
        szm = self._sz.get_mode()

        axl = cfg.AXIS_LEAD_X
        ayl = cfg.AXIS_LEAD_Y
        azl = cfg.AXIS_LEAD_Z

        steps_r = _mm_to_steps(r, sxa, sxm, axl)
        steps_x = _mm_to_steps(x, sxa, sxm, axl)
        steps_y = _mm_to_steps(y, sya, sym, ayl)

        if plane == "XY":
            pps_x = _mm_per_min_to_pps(feed_rate, sxa, sxm, axl)
            pps_y = _mm_per_min_to_pps(feed_rate, sya, sym, ayl)
            return _plan_interpolated_arc(steps_r, steps_x, steps_y, pps_x, pps_y, is_cw)
        elif plane == "XZ":
            pps_x = _mm_per_min_to_pps(feed_rate, sxa, sxm, axl)
            pps_z = _mm_per_min_to_pps(feed_rate, sza, szm, azl)
            return _plan_interpolated_arc(steps_r, steps_x, steps_y, pps_x, pps_z, is_cw)
        elif plane == "YZ":
            pps_y = _mm_per_min_to_pps(feed_rate, sya, sym, ayl)
            pps_z = _mm_per_min_to_pps(feed_rate, sza, szm, azl)
            return _plan_interpolated_arc(steps_r, steps_x, steps_y, pps_y, pps_z, is_cw)
        else:
            return None
