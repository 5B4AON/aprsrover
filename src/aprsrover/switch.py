"""
switch.py

Provides a modular, testable interface for managing GPIO-connected switches on a Raspberry Pi.
Supports synchronous and asynchronous monitoring, and allows registration of callbacks for switch
state changes.

Usage example:
    from aprsrover.switch import Switch, SwitchEvent, SwitchObserver

    def on_switch_change(event: SwitchEvent) -> None:
        print(f"Switch {event.pin} changed to {'ON' if event.state else 'OFF'}")

    switch = Switch(pin=17)
    switch.add_observer(on_switch_change)
    switch.start_monitoring()

    # ... later ...
    switch.set_state(True)  # Turn switch ON

    # For async usage, see async_monitor() method docstring.
"""

from typing import Callable, List, Optional, Protocol, Any, Literal
import threading
import sys
import platform

# Only import RPi.GPIO if running on a Raspberry Pi
if platform.system() == "Linux" and ("arm" in platform.machine() or "aarch64" in platform.machine()):
    try:
        import RPi.GPIO as GPIO
    except ImportError:
        GPIO = None  # type: ignore
else:
    GPIO = None  # type: ignore

class SwitchError(Exception):
    """Custom exception for switch-related errors."""
    pass

class SwitchEvent:
    """
    Represents a switch state change event.

    Attributes:
        pin (int): The BCM pin number.
        state (bool): The new state of the switch (True for ON, False for OFF).
    """
    def __init__(self, pin: int, state: bool) -> None:
        self.pin = pin
        self.state = state

SwitchObserver = Callable[[SwitchEvent], None]

class GPIOInterface(Protocol):
    BCM: Any
    IN: Any
    OUT: Any
    PUD_UP: Any

    def setmode(self, mode: Any) -> None: ...
    def setup(self, pin: int, mode: Any, pull_up_down: Any = ...) -> None: ...
    def input(self, pin: int) -> int: ...
    def output(self, pin: int, value: int) -> None: ...
    def cleanup(self, pin: Optional[int] = ...) -> None: ...
    def add_event_detect(self, pin: int, edge: Any, callback: Any, bouncetime: int = ...) -> None: ...
    def remove_event_detect(self, pin: int) -> None: ...

class Switch:
    """
    Represents a GPIO-connected switch, configurable as input or output.

    Args:
        pin (int): The BCM pin number.
        direction (Literal["IN", "OUT"]): Pin direction, either "IN" or "OUT".
        gpio (Optional[GPIOInterface]): GPIO interface (for testing/mocking).
        debounce_ms (int): Debounce time in milliseconds.

    Raises:
        SwitchError: If GPIO is not available or setup fails.

    Thread Safety:
        All public methods are thread-safe.

    Example:
        >>> switch = Switch(pin=17, direction="OUT")
        >>> switch.set_state(True)
        >>> print(switch.get_state())
    """
    def __init__(
        self,
        pin: int,
        direction: Literal["IN", "OUT"],
        gpio: Optional[GPIOInterface] = None,
        debounce_ms: int = 50
    ) -> None:
        self.pin = pin
        self.direction = direction
        self._gpio = gpio or GPIO
        self._debounce_ms = debounce_ms
        self._observers: List[SwitchObserver] = []
        self._lock = threading.Lock()
        self._monitor_thread: Optional[threading.Thread] = None
        self._monitoring = threading.Event()
        self._last_state: Optional[bool] = None
        self._output_state: bool = False  # Only used if direction == "OUT"

        if self._gpio is None:
            raise SwitchError("RPi.GPIO library not available.")

        self._setup_gpio()

    def _setup_gpio(self) -> None:
        try:
            self._gpio.setmode(self._gpio.BCM)
            if self.direction == "IN":
                self._gpio.setup(self.pin, self._gpio.IN, pull_up_down=self._gpio.PUD_UP)
            elif self.direction == "OUT":
                self._gpio.setup(self.pin, self._gpio.OUT)
                self._gpio.output(self.pin, int(not self._output_state))
            else:
                raise ValueError("direction must be 'IN' or 'OUT'")
        except Exception as exc:
            raise SwitchError(f"Failed to setup GPIO pin {self.pin}: {exc}")

    def get_state(self) -> bool:
        """
        Returns the current state of the switch.

        Returns:
            bool: True if ON, False if OFF.
        """
        if self.direction == "IN":
            return self._gpio.input(self.pin) == 0
        else:
            return self._output_state

    def set_state(self, state: bool) -> None:
        """
        Sets the switch state (only if configured as output).

        Args:
            state (bool): True to turn ON, False to turn OFF.

        Raises:
            SwitchError: If not output-capable or unable to set state.
        """
        if self.direction != "OUT":
            raise SwitchError("Cannot set state on input-configured switch.")
        try:
            self._gpio.output(self.pin, int(not state))
            with self._lock:
                prev_state = self._output_state
                self._output_state = state
            if prev_state != state:
                self._notify_observers(state)
        except Exception as exc:
            raise SwitchError(f"Failed to set state for pin {self.pin}: {exc}")

    def add_observer(self, observer: SwitchObserver) -> None:
        """
        Registers a callback for switch state changes.

        Args:
            observer (SwitchObserver): Callback to invoke on state change.
        """
        with self._lock:
            self._observers.append(observer)

    def remove_observer(self, observer: SwitchObserver) -> None:
        """
        Unregisters a previously registered observer.

        Args:
            observer (SwitchObserver): The observer to remove.
        """
        with self._lock:
            try:
                self._observers.remove(observer)
            except ValueError:
                pass  # Ignore if observer is not registered

    def _notify_observers(self, state: bool) -> None:
        event = SwitchEvent(self.pin, state)
        with self._lock:
            for observer in list(self._observers):
                try:
                    observer(event)
                except Exception:
                    pass  # Optionally log

    def start_monitoring(self) -> None:
        """
        Starts a background thread to monitor switch state changes and notify observers.

        Thread-safe. Call `stop_monitoring()` to stop.
        """
        if self._monitor_thread and self._monitor_thread.is_alive():
            return
        self._monitoring.set()
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()

    def stop_monitoring(self) -> None:
        """
        Stops background monitoring.
        """
        self._monitoring.clear()
        if self._monitor_thread:
            self._monitor_thread.join(timeout=1)

    def _monitor_loop(self) -> None:
        import time
        self._last_state = self.get_state()
        while self._monitoring.is_set():
            state = self.get_state()
            if state != self._last_state:
                self._notify_observers(state)
                self._last_state = state
            time.sleep(self._debounce_ms / 1000.0)

    async def async_monitor(self, poll_interval: float = 0.05) -> None:
        """
        Asynchronously monitors the switch and notifies observers on state changes.

        Args:
            poll_interval (float): Polling interval in seconds.

        Usage example:
            import asyncio
            from aprsrover.switch import Switch

            async def main():
                switch = Switch(pin=17, direction="OUT")
                switch.add_observer(lambda e: print(f"Switch changed: {e.state}"))
                await switch.async_monitor()

            asyncio.run(main())
        """
        self._last_state = self.get_state()
        import asyncio
        while True:
            state = self.get_state()
            if state != self._last_state:
                self._notify_observers(state)
                self._last_state = state
            await asyncio.sleep(poll_interval)

    def cleanup(self) -> None:
        """
        Cleans up GPIO resources for this pin.
        """
        self._gpio.cleanup(self.pin)