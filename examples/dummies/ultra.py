from aprsrover.ultra import GPIOInterface
from typing import Any, Optional
import time

class DummyUltra(GPIOInterface):
    """
    Dummy GPIO backend for ultrasonic sensor testing and examples.

    Simulates the echo pin timing so that the measured distance matches the value set by
    set_distance(), to two decimal points. This allows deterministic and realistic testing
    of the UltraSonic class without hardware.

    Usage:
        dummy = DummyUltra()
        dummy.set_distance(42.0)
        # Use with UltraSonic(gpio=dummy)
    """
    BCM: str = "BCM"
    IN: str = "IN"
    OUT: str = "OUT"
    LOW: int = 0
    HIGH: int = 1

    def __init__(self) -> None:
        self.mode: Optional[str] = None
        self.pin_modes: dict[int, Any] = {}
        self.pin_values: dict[int, int] = {}
        self.cleanup_calls: list[Optional[int]] = []
        self.simulated_distance_cm: float = 100.0  # Default simulated distance
        self._last_output_pin: Optional[int] = None
        self._last_output_value: Optional[int] = None
        self._echo_state: int = self.LOW
        self._triggered: bool = False
        self._echo_start_time: Optional[float] = None
        self._echo_end_time: Optional[float] = None
        self._echo_pin: Optional[int] = None

    def setmode(self, mode: Any) -> None:
        self.mode = mode

    def setup(self, pin: int, mode: Any) -> None:
        self.pin_modes[pin] = mode
        self.pin_values[pin] = self.LOW

    def output(self, pin: int, value: int) -> None:
        self.pin_values[pin] = value
        self._last_output_pin = pin
        self._last_output_value = value
        # Simulate trigger pulse: when trigger pin goes HIGH then LOW, set up echo timing
        if value == self.HIGH:
            self._triggered = True
        elif value == self.LOW and self._triggered:
            # On falling edge, schedule echo pulse
            self._triggered = False
            # Use float for all calculations
            pulse_duration = (self.simulated_distance_cm * 2) / 34300.0
            now = time.monotonic()
            self._echo_start_time = now + 0.0001
            self._echo_end_time = self._echo_start_time + pulse_duration
            self._echo_state = self.LOW  # Will be set HIGH when input() is called at the right time

    def input(self, pin: int) -> int:
        """
        Simulate echo pin: goes HIGH for the correct duration based on set_distance().
        """
        now = time.monotonic()
        if self._echo_start_time is not None and self._echo_end_time is not None:
            if self._echo_start_time <= now < self._echo_end_time:
                return self.HIGH
            elif now >= self._echo_end_time:
                # Reset after pulse
                self._echo_start_time = None
                self._echo_end_time = None
                return self.LOW
        return self.LOW

    def cleanup(self, pin: Optional[int] = None) -> None:
        self.cleanup_calls.append(pin)

    def set_distance(self, distance_cm: float) -> None:
        """
        Set the simulated distance (in cm) for the next measurement.
        Accepts float.
        """
        self.simulated_distance_cm = float(distance_cm)
