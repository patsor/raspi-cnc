#!/usr/bin/env python

import time

import RPi.GPIO as GPIO


def _busy_wait(dt):
    """Implementation of busy wait for time critical step intervals."""
    current_time = time.time()
    while (time.time() < current_time+dt):
        pass


def main():

    step_pin = 15
    dir_pin = 22
    #    ena_pin = 12

    dt = 0.001

    GPIO.setmode(GPIO.BOARD)

    GPIO.setup(step_pin, GPIO.OUT)
    GPIO.setup(dir_pin, GPIO.OUT)
#    GPIO.setup(ena_pin, GPIO.OUT)

#    GPIO.output(ena_pin, 1)
#    time.sleep(0.1)
    
    GPIO.output(dir_pin, 0)
    time.sleep(0.01)

    for n in range(10):
        print("Round", n)
        for i in range(3200):
            GPIO.output(step_pin, 1)
            _busy_wait(dt)
            #time.sleep(dt)
            GPIO.output(step_pin, 0)
            _busy_wait(dt)
            #time.sleep(dt)

        if n % 2 == 0:
            GPIO.output(dir_pin, 1)
            print("Switching direction to CCW")
        else:
            GPIO.output(dir_pin, 0)
            print("Switching direction to CW")
        time.sleep(0.2)
        

#    GPIO.output(ena_pin, 1)
        
    GPIO.cleanup()

if __name__ == "__main__":
    main()
