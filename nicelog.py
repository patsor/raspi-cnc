#!/usr/bin/env python

from __future__ import print_function

def nprint(text, type="ok"):
    if type == "ok":
        print("\r [ ] {}...".format(text), end="")
    elif type == "info":
        print("\r [ ] {}.".format(text), end="")

def ninfo(text):
    print(" [info] {}.".format(text))

def nflush(text, type="ok"):
    if type == "ok":
        print("\r [ ok ] {}...done.".format(text))
    elif type == "info":
        print("\r [info] {}.".format(text))
                
