"""
switch.py

Provides a modular, testable interface for managing GPIO-connected switches on a Raspberry Pi.

Features:

- Supports both input and output configurations.
- Allows synchronous and asynchronous state monitoring.
- Provides a callback mechanism for state changes.
- Thread-safe operations for multi-threaded applications.
- Custom exception handling for GPIO errors.
- Dependency injection for GPIO interface, allowing testing with mock objects.
- Supports GPIO cleanup to release resources.

Requires:

- Python 3.10+
- RPi.GPIO (if running on Raspberry Pi)

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
import logging
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
        self._event_detected: bool = False

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

    def _event_callback(self, pin: int) -> None:
        """Internal callback for GPIO event detection."""
        state = self.get_state()
        self._notify_observers(state)

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
            logging.debug(f"Setting pin {self.pin} to {'ON' if state else 'OFF'}")
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
        Starts monitoring for input state changes using event detection if available,
        otherwise falls back to polling in a background thread.

        This method is synchronous and intended for use in traditional or multi-threaded
        applications. It will start a background thread to poll the switch state if
        event detection is not available. Observers are notified on state changes.

        Use `stop_monitoring()` to stop monitoring and clean up resources.

        Raises:
            SwitchError: If called on a switch not configured as input.

        Example:
            switch = Switch(pin=17, direction="IN")
            switch.add_observer(lambda e: print(f"Switch changed: {e.state}"))
            switch.start_monitoring()
            # ... later ...
            switch.stop_monitoring()
        """
        if self.direction != "IN":
            raise SwitchError("Monitoring is only supported for input-configured switches.")

        if self._monitor_thread and self._monitor_thread.is_alive():
            return

        # Try to use event detection if available
        if hasattr(self._gpio, "add_event_detect"):
            try:
                self._gpio.add_event_detect(
                    self.pin,
                    getattr(self._gpio, "BOTH", 3),  # 3 is BOTH for RPi.GPIO
                    callback=self._event_callback,
                    bouncetime=self._debounce_ms
                )
                self._event_detected = True
                return
            except Exception as exc:
                logging.warning(f"Event detection not available, falling back to polling: {exc}")

        # Fallback: polling
        self._monitoring.set()
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()

    def stop_monitoring(self) -> None:
        """
        Stops background monitoring or removes event detection.
        """
        if self._event_detected:
            try:
                self._gpio.remove_event_detect(self.pin)
            except Exception:
                pass
            self._event_detected = False
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

        If event detection is available, this method sets up event callbacks and returns
        immediately (observers will be notified via callbacks). If event detection is not
        available, it polls the pin state in an async loop at the specified interval.

        This method is intended for use in asyncio-based applications. It should be
        awaited or run as an asyncio task.

        Args:
            poll_interval (float): Polling interval in seconds (used only if polling).

        Raises:
            SwitchError: If called on a switch not configured as input.

        Usage example:
            import asyncio
            from aprsrover.switch import Switch

            async def main():
                switch = Switch(pin=17, direction="IN")
                switch.add_observer(lambda e: print(f"Switch changed: {e.state}"))
                await switch.async_monitor()

            asyncio.run(main())
        """
        if self.direction != "IN":
            raise SwitchError("Async monitoring is only supported for input-configured switches.")

        # Try to use event detection if available
        if hasattr(self._gpio, "add_event_detect"):
            try:
                self._gpio.add_event_detect(
                    self.pin,
                    getattr(self._gpio, "BOTH", 3),
                    callback=self._event_callback,
                    bouncetime=self._debounce_ms
                )
                self._event_detected = True
                return  # Event detection is now active; no polling needed
            except Exception as exc:
                logging.warning(f"Event detection not available, falling back to polling: {exc}")

        # Fallback: polling
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
        if self._event_detected:
            try:
                self._gpio.remove_event_detect(self.pin)
            except Exception:
                pass
            self._event_detected = False
        self._gpio.cleanup(self.pin)