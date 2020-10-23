#!/usr/bin/env python

from argparse import ArgumentParser
import logging
import math
import sys
import threading
import time

# Uncomment for testing
# import RPi.GPIO as GPIO

import config as cfg


def _configure_ramp_trapezoidal(vm, mode, step_angle, lead, accel):
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


def _add_ramp(interval, ramp, step_delay):
    masked_interval = []
    interval_len = len(interval)
    ramp_len = len(ramp)
    for i, pulse in enumerate(interval):
        if i < ramp_len and i < interval_len / 2:
            masked_interval.append((pulse, ramp[i]/2))
        elif i >= interval_len - ramp_len and i >= interval_len / 2:
            masked_interval.append((pulse, ramp[interval_len - i - 1]/2))
        else:
            masked_interval.append((pulse, step_delay/2))

    return masked_interval


def _convert_mm_per_min_to_pulse(value, lead, step_angle, mode):
    return lead * 60 / value / mode / (360 / step_angle)


class Stepper(object):
    def __init__(self, name, debug=False):
        stepper_cfg = cfg.steppers[name]
        self.name = name
        self.driver = stepper_cfg["driver"]
        self.mode = stepper_cfg["mode"]
        self.direction = stepper_cfg["direction"]
        self.step_angle = stepper_cfg["step_angle"]
        self.gpios = stepper_cfg["gpios"]

        axis_cfg = cfg.axes[name]
        self.lead = axis_cfg["lead"]
        self.ramp_type = axis_cfg["ramp_type"]
        self.accel = axis_cfg["accel"]

        self.speed = 0.0
        self.set_speed(axis_cfg["traversal_rate"])

        self.logger = logging.getLogger(self.name)
        self.debug = debug

        if self.driver in cfg.drivers:
            self.modes = cfg.drivers[self.driver]["modes"]
        else:
            print("Error: Could not load config for {}".format(self.driver))
            sys.exit(1)

        self.dirs = {
            "CW": False,
            "CCW": True
        }

        if not self.debug:
            self.init()

    def init(self):
        GPIO.setmode(GPIO.BOARD)
        GPIO.setwarnings(False)
        GPIO.setup(list(self.gpios.values()), GPIO.OUT)
        GPIO.output(list(self.gpios.values()), False)
        self.set_mode(self.mode, initial=True)
        self.set_direction(self.direction, initial=True)

    def configure_ramp_trapezoidal(self, vm):
        self.ramp = _configure_ramp_trapezoidal(
            vm, self.mode, self.step_angle, self.lead, self.accel)

    def configure_ramp_sigmoidal(self, vm):
        self.ramp = _configure_ramp_sigmoidal(
            vm, self.mode, self.step_angle, self.lead, self.accel)

    def configure_ramp_polynomial(self, vm):
        self.ramp = _configure_ramp_polynomial(
            vm, self.mode, self.step_angle, self.lead, self.accel)

    def enable(self):
        """Activate sleep mode"""
        if not self.debug:
            GPIO.output(self.gpios["sleep"], True)
            time.sleep(0.1)

    def disable(self):
        """Activate sleep mode"""
        if not self.debug:
            GPIO.output(self.gpios["sleep"], False)
            time.sleep(0.1)

    def get_mode(self):
        """Get mode of stepper motor"""
        return self.mode

    def set_mode(self, mode, initial=False):
        """Set mode of stepper motor"""
        # Do not change mode if input mode equals current mode
        if self.mode == mode and not initial:
            return
        if mode not in self.modes:
            raise ValueError("Mode not available: {}".format(mode))
        bits = self.modes[mode]
        self.logger.debug(
            "{} - Setting Microstepping Mode: 1/{} {}".format(self.name, mode, bits))

        if not self.debug:
            GPIO.output((self.gpios["m2"], self.gpios["m1"],
                         self.gpios["m0"]), (bits[0], bits[1], bits[2]))
            time.sleep(0.001)

        if self.ramp_type == "trapezoidal":
            self.configure_ramp_trapezoidal(self.speed)
        elif self.ramp_type == "sigmoidal":
            self.configure_ramp_sigmoidal(self.speed)

        self.mode = mode

    def get_direction(self):
        """Get direction of stepper motor"""
        return self.direction

    def set_direction(self, direction, initial=False):
        """Set direction of stepper motor"""
        # Do not change direction if input direction equals current direction
        if self.direction == direction and not initial:
            return
        self.logger.debug(
            "{} - Setting direction: {}".format(self.name, direction))
        if not self.debug:
            GPIO.output(self.gpios["dir"], self.dirs[direction])
            time.sleep(0.001)
        self.direction = direction

    def get_speed(self):
        return self.speed

    def set_speed(self, speed):
        if self.speed == speed:
            return

        if self.ramp_type == "trapezoidal":
            self.configure_ramp_trapezoidal(speed)
        elif self.ramp_type == "sigmoidal":
            self.configure_ramp_sigmoidal(speed)

        self.speed = speed
        self.step_delay = _convert_mm_per_min_to_pulse(
            speed, self.lead, self.step_angle, self.mode)

    def step(self, interval):
        gpio_step = self.gpios["step"]
        masked_interval = _add_ramp(interval, self.ramp, self.step_delay)

        for i, delay in masked_interval:
            if i == -1:
                self.set_direction("CCW")
            else:
                self.set_direction("CW")
            for ele in (True, False):
                if i:
                    GPIO.output(gpio_step, ele)
                time.sleep(delay)


def main():
    parser = ArgumentParser(description="Invokes stepper motor movement")
    parser.add_argument("-n", "--name", dest="name",
                        help="Specify configuration for stepper motor based on config", default="default")
    parser.add_argument("-s", "--steps", dest="steps", type=int,
                        help="Specify number of steps for the motor to move", default=1)
    parser.add_argument("-m", "--mode", dest="mode",
                        type=int, help="Specify microstepping mode")
    parser.add_argument("-d", "--direction", dest="direction",
                        choices=["CW", "CCW"], help="Specify direction of movement")
    args = parser.parse_args()

    s = Stepper(
        args.name,
        debug=False
    )

    s.enable()

    if args.mode:
        s.set_mode(args.mode)

    if args.direction:
        s.set_direction(args.direction)

    interval = [
        1 if args.direction == "CW" else -1 for step in range(args.steps)
    ]

    s.step(interval)

    s.disable()
    GPIO.output(list(s["gpios"].values()), False)
    GPIO.cleanup()


if __name__ == "__main__":
    main()
