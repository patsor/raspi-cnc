
import os

# Global settings
module_dir = os.path.dirname(os.path.realpath(__file__))
coord_file = os.path.join(module_dir, "coord.json")
logfile = os.path.join(module_dir, "logs", "main.log")


# Constants
# Define step angle for each stepper
STEPPER_STEP_ANGLE_X = 1.8
STEPPER_STEP_ANGLE_Y = 1.8
STEPPER_STEP_ANGLE_Z = 1.8

# Define stepper modes
STEPPER_MODE_X = 8
STEPPER_MODE_Y = 8
STEPPER_MODE_Z = 8

AXIS_LEAD_X = 5
AXIS_LEAD_Y = 5
AXIS_LEAD_Z = 5

# Define axis speeds in mm/min
AXIS_TRAVERSAL_MM_PER_MIN_X = 2000.0
AXIS_TRAVERSAL_MM_PER_MIN_Y = 2000.0
AXIS_TRAVERSAL_MM_PER_MIN_Z = 2000.0

AXIS_FEED_MM_PER_MIN_X = 1200.0
AXIS_FEED_MM_PER_MIN_Y = 1200.0
AXIS_FEED_MM_PER_MIN_Z = 1200.0

# Define axis limits
AXIS_LIMITS_X = (0.0, 800.0)
AXIS_LIMITS_Y = (0.0, 600.0)
AXIS_LIMITS_Z = (0.0, 100.0)

# Define inverted axes
AXIS_POLARITY_X = False
AXIS_POLARITY_Y = False
AXIS_POLARITY_Z = True

# Define axis acceleration in mm/s^2 and ramp type
AXIS_ACCELERATION_X = 80.0
AXIS_ACCELERATION_Y = 80.0
AXIS_ACCELERATION_Z = 80.0

AXIS_RAMP_TYPE_X = "sigmoidal"
AXIS_RAMP_TYPE_Y = "sigmoidal"
AXIS_RAMP_TYPE_Z = "sigmoidal"


steppers = {
    "default": {
        "driver": "DRV8825",
        "direction": "CW",
        "gpios": {
            "dir": 10,       # DIR
            "step": 17,      # STEP
            "sleep": 1,     # SLEEP
        },
    },
    "X": {
        "driver": "DRV8825",
        "direction": "CW",
        "gpios": {
            "dir": 23,       # DIR
            "step": 17,      # STEP
            "sleep": 1,     # SLEEP
        },
    },
    "Y": {
        "driver": "DRV8825",
        "direction": "CW",
        "gpios": {
            "dir": 24,       # DIR
            "step": 27,     # STEP
            "sleep": 1,    # SLEEP
        },
    },
    "Z": {
        "driver": "DRV8825",
        "direction": "CW",
        "gpios": {
            "dir": 25,       # DIR
            "step": 22,      # STEP
            "sleep": 1,     # SLEEP
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
    },
    "DM556T": {
        # Microstepping modes of DM556T
        # This dictionary is just for the sake of completeness
        # as the user can only manually select microstepping mode
        # directly on the module through DIP switches
        # Microstep: (SW5, SW6, SW7, SW8) (1: on, 0: off)
        "modes": {
            1: (1, 1, 1, 1),
            2: (0, 1, 1, 1),
            4: (1, 0, 1, 1),
            8: (0, 0, 1, 1),
            16: (1, 1, 0, 1),
            32: (0, 1, 0, 1),
            64: (1, 0, 0, 1),
            128: (0, 0, 0, 1)
        }
    }
}
