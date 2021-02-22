#!/usr/bin/env python

import time

import RPi.GPIO as GPIO


def _busy_wait(dt):
    """Implementation of busy wait for time critical step intervals."""
    current_time = time.time()
    while (time.time() < current_time+dt):
        pass


def main():

    step_pin = 17
    dir_pin = 10
    
    GPIO.setmode(GPIO.BCM)

    GPIO.setup(step_pin, GPIO.OUT)

    GPIO.setup(dir_pin, GPIO.OUT)

    GPIO.output(dir_pin, 1)

    for i in range(6400):
        GPIO.output(step_pin, 1)
        _busy_wait(0.0002)
        GPIO.output(step_pin, 0)
        _busy_wait(0.0002)

    GPIO.output(dir_pin, 0)
        
    for i in range(6400):
        GPIO.output(step_pin, 1)
        _busy_wait(0.0002)
        GPIO.output(step_pin, 0)
        _busy_wait(0.0002)

        

    GPIO.cleanup()

if __name__ == "__main__":
    main()
