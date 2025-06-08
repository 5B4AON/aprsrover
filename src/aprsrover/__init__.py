"""
aprsrover - APRS Rover Utilities

A modular Python library for controlling a rover using APRS, GPS, GPIO switches, and PWM tracks.  
Designed for easy integration, asynchronous operation, and high testability with abstracted hardware access.
"""

import logging

__version__ = "0.1.0"

# Default logging configuration for the aprsrover package.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)

# Users can override this configuration in their own scripts if desired.
