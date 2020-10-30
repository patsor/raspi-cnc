#!/usr/bin/env python

import spidev
from time import sleep


class DRV8711(object):

    __REG_CTRL = 0x00
    __REG_TORQUE = 0x01
    __REG_OFF = 0x02
    __REG_BLANK = 0x03
    __REG_DECAY = 0x04
    __REG_STALL = 0x05
    __REG_DRIVE = 0x06
    __REG_STATUS = 0x07

    def __init__(self, cs=0):
        self.device = spidev.SpiDev()
        self.device.open(0, cs)
        self.device.mode = 0
        self.device.cshigh = False

    def get_control(self):
        return self.read_register(__REG_CTRL)

    def read_register(self, address):
        return self.device.xfer2([address, 0x00])


def main():
    drv8711 = DRV8711()
    drv8711.get_control()


if __name__ == "__main__":
    main()
