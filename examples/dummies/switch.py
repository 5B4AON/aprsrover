from aprsrover.switch import GPIOInterface
from typing import Any, Optional, Callable

class DummySwitch(GPIOInterface):
    """
    Dummy switch backend for testing and examples.
    Simulates a hardware switch/button.
    """
    BCM: str = "BCM"
    IN: str = "IN"
    OUT: str = "OUT"
    PUD_UP: str = "PUD_UP"

    def __init__(self) -> None:
        self.mode: Optional[str] = None
        self.pin_modes: dict[int, tuple[Any, Optional[Any]]] = {}
        self.pin_values: dict[int, int] = {}
        self.cleanup_calls: list[Optional[int]] = []
        self.output_calls: list[tuple[int, int]] = []
        self.event_detected: dict[int, Callable[[int], None]] = {}

    def setmode(self, mode: Any) -> None:
        """Set the GPIO mode."""
        self.mode = mode

    def setup(self, pin: int, mode: Any, pull_up_down: Any = None) -> None:
        """Configure a pin as input or output."""
        self.pin_modes[pin] = (mode, pull_up_down)
        if mode == self.OUT:
            self.pin_values[pin] = 1  # Default OFF
        elif mode == self.IN:
            self.pin_values.setdefault(pin, 1)  # Default pulled up

    def input(self, pin: int) -> int:
        """Read the value of a pin."""
        return self.pin_values.get(pin, 1)

    def output(self, pin: int, value: int) -> None:
        """Set the value of an output pin."""
        self.pin_values[pin] = value
        self.output_calls.append((pin, value))

    def cleanup(self, pin: Optional[int] = None) -> None:
        """Record cleanup calls for testing."""
        self.cleanup_calls.append(pin)

    def add_event_detect(
        self, pin: int, edge: Any, callback: Callable[[int], None], bouncetime: int = 50
    ) -> None:
        """Register a callback for pin state changes."""
        self.event_detected[pin] = callback

    def remove_event_detect(self, pin: int) -> None:
        """Remove a registered event callback."""
        if pin in self.event_detected:
            del self.event_detected[pin]

    def simulate_input(self, pin: int, state: bool) -> None:
        """
        Simulate an input event for a given pin.

        Args:
            pin: The GPIO pin number to simulate input on.
            state: The boolean state to set (True for HIGH, False for LOW).

        Raises:
            ValueError: If the pin is not configured as input.

        Usage example:
            dummy = DummySwitch()
            dummy.setup(17, DummySwitch.IN)
            dummy.simulate_input(17, True)
        """
        mode, _ = self.pin_modes.get(pin, (None, None))
        if mode != self.IN:
            raise ValueError(f"Pin {pin} is not configured as input (IN).")
        self.pin_values[pin] = int(state)
        # Trigger event callback if registered
        callback = self.event_detected.get(pin)
        if callback:
            callback(pin)
