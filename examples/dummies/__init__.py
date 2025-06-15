"""
Centralized dummy backend implementations for aprsrover examples.
Import dummies from this module in all dummy backend examples.
"""

from .aprs import DummyAPRS
from .gps import DummyGPS
from .hw_info import DummyHWInfo
from .switch import DummySwitch
from .pwm import DummyPWM
from .dht import DummyDHT
from .ultra import DummyUltra
from .neopixel import DummyNeoPixelBackend
