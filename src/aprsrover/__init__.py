"""
aprsrover - APRS Rover Utilities

This package provides utilities for APRS messaging, GPS, and rover track control.
"""

import logging

__version__ = "0.1.0"

# Default logging configuration for the aprsrover package.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)

# Users can override this configuration in their own scripts if desired.
