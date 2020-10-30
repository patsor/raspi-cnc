
import os

# Global settings
module_dir = os.path.dirname(os.path.realpath(__file__))
coord_file = os.path.join(module_dir, "coord.json")
logfile = os.path.join(module_dir, "logs", "main.log")

steppers = {
    "default": {
        "driver": "DRV8825",
        "mode": 2,
        "direction": "CW",
        "step_angle": 1.8,
        "gpios": {
            "dir": 16,       # DIR
            "step": 18,      # STEP
            "sleep": 31,     # SLEEP
            "m0": 11,        # M0
            "m1": 13,        # M1
            "m2": 15,        # M2
        },
    },
    "X": {
        "driver": "DRV8825",
        "mode": 2,
        "direction": "CW",
        "step_angle": 1.8,
        "gpios": {
            "dir": 16,       # DIR
            "step": 18,      # STEP
            "sleep": 31,     # SLEEP
            "m0": 11,        # M0
            "m1": 13,        # M1
            "m2": 15,        # M2
        },
    },
    "Y": {
        "driver": "DRV8825",
        "mode": 2,
        "direction": "CW",
        "step_angle": 1.8,
        "gpios": {
            "dir": 8,       # DIR
            "step": 10,     # STEP
            "sleep": 29,    # SLEEP
            "m0": 3,        # M0
            "m1": 5,        # M1
            "m2": 7,        # M2
        },
    },
    "Z": {
        "driver": "DRV8825",
        "mode": 2,
        "direction": "CW",
        "step_angle": 1.8,
        "gpios": {
            "dir": 38,       # DIR
            "step": 40,      # STEP
            "sleep": 32,     # SLEEP
            "m0": 33,        # M0
            "m1": 35,        # M1
            "m2": 37,        # M2
        },
    },
}

drivers = {
    "DRV8825": {
        # Microstepping modes of DRV8825
        # Microstepping mode 1/n: M2, M1, M0
        # Example: 1/2 (Half step): M2=0, M1=0, M0=1
        "modes": {
            1: (0, 0, 0),
            2: (0, 0, 1),
            4: (0, 1, 0),
            8: (0, 1, 1),
            16: (1, 0, 0),
            32: (1, 1, 0)
        },
    },
    "TB67S249FTG": {
        # Microstepping modes of TB67S249FTG
        # Microstepping mode 1/n: M2, M1, M0
        "modes": {
            0: (0, 0, 0),
            1: (1, 0, 0),
            2: (0, 1, 0),  # non-circular half step (100% current, high torque)
            # 2: (0, 0, 1), # circular half step (71% current, medium torque)
            4: (1, 1, 0),
            8: (1, 0, 1),
            16: (0, 1, 1),
            32: (1, 1, 1)
        },
    },
    "DRV8711": {
        # Microstepping modes of DRV8711
        # Microstepping mode 1/n: M3, M2, M1, M0
        "modes": {
            1: (0, 0, 0, 0),
            2: (0, 0, 0, 1),
            4: (0, 0, 1, 0),
            8: (0, 0, 1, 1),
            16: (0, 1, 0, 0),
            32: (0, 1, 0, 1),
            64: (0, 1, 1, 0),
            128: (0, 1, 1, 1),
            256: (1, 0, 0, 0),
        },
    }
}

axes = {
    "X": {
        "traversal_rate": 3750.0,     # in mm/min
        "feed_rate": 2000.0,  # in mm/min
        "limits": [
            0.0,
            800.0
        ],
        "polarity": False,
        "lead": 5,     # in mm
        "ramp_type": "sigmoidal",
        "accel": 80.0   # in mm/s^2
    },
    "Y": {
        "traversal_rate": 3750.0,     # in mm/min
        "feed_rate": 2000.0,  # in mm/min
        "limits": [
            0.0,
            600.0
        ],
        "polarity": False,
        "lead": 5,     # in mm
        "ramp_type": "sigmoidal",
        "accel": 80.0   # in mm/s^2
    },
    "Z": {
        "traversal_rate": 3750.0,     # in mm/min
        "feed_rate": 2000.0,  # in mm/min
        "limits": [
            0.0,
            100.0
        ],
        "polarity": True,
        "lead": 5,     # in mm
        "ramp_type": "sigmoidal",
        "accel": 80.0   # in mm/s^2
    }
}
