from aprsrover.switch import GPIOInterface
from typing import Any, Optional, Callable

class DummySwitch(GPIOInterface):
    """
    Dummy switch backend for testing and examples.
    Simulates a hardware switch/button.
    """
    BCM = "BCM"
    IN = "IN"
    OUT = "OUT"
    PUD_UP = "PUD_UP"

    def __init__(self) -> None:
        self.mode = None
        self.pin_modes: dict[int, tuple[Any, Optional[Any]]] = {}
        self.pin_values: dict[int, int] = {}
        self.cleanup_calls: list[Optional[int]] = []
        self.output_calls: list[tuple[int, int]] = []
        self.event_detected: dict[int, Callable] = {}

    def setmode(self, mode: Any) -> None:
        self.mode = mode

    def setup(self, pin: int, mode: Any, pull_up_down: Any = None) -> None:
        self.pin_modes[pin] = (mode, pull_up_down)
        if mode == self.OUT:
            self.pin_values[pin] = 1  # Default OFF
        elif mode == self.IN:
            self.pin_values.setdefault(pin, 1)  # Default pulled up

    def input(self, pin: int) -> int:
        return self.pin_values.get(pin, 1)

    def output(self, pin: int, value: int) -> None:
        self.pin_values[pin] = value
        self.output_calls.append((pin, value))

    def cleanup(self, pin: Optional[int] = None) -> None:
        self.cleanup_calls.append(pin)

    def add_event_detect(self, pin: int, edge: Any, callback: Any, bouncetime: int = 50) -> None:
        self.event_detected[pin] = callback

    def remove_event_detect(self, pin: int) -> None:
        if pin in self.event_detected:
            del self.event_detected[pin]
