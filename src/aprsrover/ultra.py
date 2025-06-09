"""
ultra.py

Provides a modular, testable interface for reading values from an ultrasonic distance sensor (e.g., HC-SR04) on a Raspberry Pi.

Features:
- Supports both synchronous and asynchronous distance measurement.
- Allows registering observers for distance updates.
- Thread-safe operations for multi-threaded applications.
- Custom exception handling for GPIO errors.
- Dependency injection for GPIO interface, allowing testing with mock objects.
- Detects if running on a Raspberry Pi and uses RPi.GPIO if available.
- Provides temperature compensation for distance measurements using the
  `UltraSonic.adjust_measurement_based_on_temp()` class method, which adjusts the measured
  distance based on the actual ambient temperature for improved accuracy.

Requires:
- Python 3.10+
- RPi.GPIO (if running on Raspberry Pi)

Usage example:
    from aprsrover.ultra import UltraSonic, UltraSonicEvent
    def on_distance(event: UltraSonicEvent):
        print(f"Distance: {event.distance_cm:.2f} cm")
    ultra = UltraSonic(trigger_pin=23, echo_pin=24)
    ultra.add_observer(on_distance)
    dist = ultra.measure_distance()
    print(f"Measured: {dist:.1f} cm")

    # Adjust measurement for actual temperature (e.g., 25.0°C)
    adjusted = UltraSonic.adjust_measurement_based_on_temp(25.0, dist)
    print(f"Adjusted for 25.0°C: {adjusted:.1f} cm")

    # For async usage, see measure_distance_async() and async_monitor() method docstrings.
"""

from typing import Callable, List, Optional, Protocol, Any
import threading
import logging
import platform
import time
import asyncio

# Only import RPi.GPIO if running on a Raspberry Pi
if platform.system() == "Linux" and ("arm" in platform.machine() or "aarch64" in platform.machine()):
    try:
        import RPi.GPIO as GPIO
    except ImportError:
        GPIO = None  # type: ignore
else:
    GPIO = None  # type: ignore

class UltraSonicError(Exception):
    """Custom exception for ultrasonic sensor errors."""
    pass

class UltraSonicEvent:
    """
    Represents a distance measurement event.
    Attributes:
        distance_cm (float): The measured distance in centimeters.
    """
    def __init__(self, distance_cm: float) -> None:
        self.distance_cm = distance_cm

UltraSonicObserver = Callable[[UltraSonicEvent], None]

class GPIOInterface(Protocol):
    BCM: Any
    IN: Any
    OUT: Any
    LOW: Any
    HIGH: Any
    def setmode(self, mode: Any) -> None: ...
    def setup(self, pin: int, mode: Any) -> None: ...
    def output(self, pin: int, value: int) -> None: ...
    def input(self, pin: int) -> int: ...
    def cleanup(self, pin: Optional[int] = ...) -> None: ...

class UltraSonic:
    """
    Represents an ultrasonic distance sensor (e.g., HC-SR04).

    Args:
        trigger_pin (int): The BCM pin number for the trigger.
        echo_pin (int): The BCM pin number for the echo.
        gpio (Optional[GPIOInterface]): GPIO interface (for testing/mocking).
        timeout (float): Timeout in seconds for distance measurement.

    Raises:
        UltraSonicError: If GPIO is not available or setup fails.

    Thread Safety:
        All public methods are thread-safe.
    """
    def __init__(
        self,
        trigger_pin: int,
        echo_pin: int,
        gpio: Optional[GPIOInterface] = None,
        timeout: float = 0.04
    ) -> None:
        self.trigger_pin = trigger_pin
        self.echo_pin = echo_pin
        self._gpio = gpio or GPIO
        self._timeout = timeout
        self._observers: List[UltraSonicObserver] = []
        self._lock = threading.Lock()
        self._monitor_thread: Optional[threading.Thread] = None
        self._monitoring = threading.Event()
        if self._gpio is None:
            raise UltraSonicError("RPi.GPIO library not available.")
        self._setup_gpio()

    def _setup_gpio(self) -> None:
        try:
            self._gpio.setmode(self._gpio.BCM)
            self._gpio.setup(self.trigger_pin, self._gpio.OUT)
            self._gpio.setup(self.echo_pin, self._gpio.IN)
            self._gpio.output(self.trigger_pin, self._gpio.LOW)
        except Exception as exc:
            raise UltraSonicError(f"Failed to setup GPIO pins: {exc}")

    def add_observer(self, observer: UltraSonicObserver) -> None:
        """
        Register a callback to be notified on each distance measurement.

        Args:
            observer: A callable accepting an UltraSonicEvent.

        Example:
            def on_distance(event: UltraSonicEvent):
                print(f"Distance: {event.distance_cm:.2f} cm")
            ultra = UltraSonic(trigger_pin=23, echo_pin=24)
            ultra.add_observer(on_distance)
        """
        with self._lock:
            self._observers.append(observer)

    def remove_observer(self, observer: UltraSonicObserver) -> None:
        """
        Unregister a previously registered observer.

        Args:
            observer: The observer to remove.
        """
        with self._lock:
            try:
                self._observers.remove(observer)
            except ValueError:
                pass

    def _notify_observers(self, distance_cm: float) -> None:
        event = UltraSonicEvent(distance_cm)
        with self._lock:
            for observer in list(self._observers):
                try:
                    observer(event)
                except Exception:
                    pass  # Optionally log

    def measure_distance(self) -> float:
        """
        Measure distance synchronously (blocking).

        Returns:
            float: Measured distance in centimeters.
        Raises:
            UltraSonicError: On timeout or hardware error.

        Example:
            ultra = UltraSonic(trigger_pin=23, echo_pin=24)
            dist = ultra.measure_distance()
            print(f"Measured: {dist:.2f} cm")
        """
        try:
            self._gpio.output(self.trigger_pin, self._gpio.LOW)
            time.sleep(0.002)
            self._gpio.output(self.trigger_pin, self._gpio.HIGH)
            time.sleep(0.00001)
            self._gpio.output(self.trigger_pin, self._gpio.LOW)
            start = time.time()
            timeout = start + self._timeout
            # Wait for echo to go HIGH
            while self._gpio.input(self.echo_pin) == 0:
                if time.time() > timeout:
                    raise UltraSonicError("Timeout waiting for echo HIGH")
            pulse_start = time.time()
            # Wait for echo to go LOW
            while self._gpio.input(self.echo_pin) == 1:
                if time.time() > timeout:
                    raise UltraSonicError("Timeout waiting for echo LOW")
            pulse_end = time.time()
            pulse_duration = pulse_end - pulse_start
            distance_cm = (pulse_duration * 34300) / 2 # Speed of sound at 20°C is 343m/s
            # Floor to one decimal place (e.g., 99.98 -> 99.9, not 100.0)
            distance_cm = int(distance_cm * 10) / 10
            self._notify_observers(distance_cm)
            return distance_cm
        except Exception as exc:
            raise UltraSonicError(f"Failed to measure distance: {exc}")

    async def measure_distance_async(self) -> float:
        """
        Measure distance asynchronously (non-blocking, for asyncio).

        Returns:
            float: Measured distance in centimeters.
        Raises:
            UltraSonicError: On timeout or hardware error.

        Example:
            import asyncio
            ultra = UltraSonic(trigger_pin=23, echo_pin=24)
            dist = await ultra.measure_distance_async()
            print(f"Measured: {dist:.2f} cm")
        """
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self.measure_distance)

    def start_monitoring(self, interval: float = 0.5) -> None:
        """
        Start background monitoring, measuring distance at regular intervals (seconds).
        Observers are notified on each measurement.

        Args:
            interval: Time in seconds between measurements (default 0.5).

        Example:
            ultra = UltraSonic(trigger_pin=23, echo_pin=24)
            ultra.add_observer(lambda e: print(e.distance_cm))
            ultra.start_monitoring(interval=1.0)
        """
        if self._monitor_thread and self._monitor_thread.is_alive():
            return
        self._monitoring.set()
        self._monitor_thread = threading.Thread(target=self._monitor_loop, args=(interval,), daemon=True)
        self._monitor_thread.start()

    def stop_monitoring(self) -> None:
        """
        Stop background monitoring.

        Example:
            ultra.stop_monitoring()
        """
        self._monitoring.clear()
        if self._monitor_thread:
            self._monitor_thread.join(timeout=1)

    def _monitor_loop(self, interval: float) -> None:
        while self._monitoring.is_set():
            try:
                dist = self.measure_distance()
                # Observers are notified in measure_distance()
            except UltraSonicError:
                pass
            time.sleep(interval)

    async def async_monitor(self, interval: float = 0.5) -> None:
        """
        Asynchronously monitor the sensor, measuring distance at regular intervals (seconds).
        Observers are notified on each measurement.

        Args:
            interval: Time in seconds between measurements (default 0.5).

        Example:
            import asyncio
            ultra = UltraSonic(trigger_pin=23, echo_pin=24)
            ultra.add_observer(lambda e: print(e.distance_cm))
            await ultra.async_monitor(interval=1.0)
        """
        while True:
            try:
                dist = await self.measure_distance_async()
                # Observers are notified in measure_distance()
            except UltraSonicError:
                pass
            await asyncio.sleep(interval)

    def cleanup(self) -> None:
        """
        Clean up GPIO resources for the trigger and echo pins.

        Example:
            ultra.cleanup()
        """
        self._gpio.cleanup(self.trigger_pin)
        self._gpio.cleanup(self.echo_pin)

    @classmethod
    def adjust_measurement_based_on_temp(
        cls,
        temperature_c: float,
        measured_distance_cm: float
    ) -> float:
        """
        Adjust a distance measurement (in cm) for the actual speed of sound at the given temperature.

        Args:
            temperature_c (float): The current temperature in degrees Celsius (to 1 decimal point).
            measured_distance_cm (float): The measured distance in cm (to 1 decimal point),
                assuming speed of sound at 20°C (343 m/s).

        Returns:
            float: The adjusted distance in cm (floored to 1 decimal point).

        Formula:
            speed_of_sound = 331.3 + 0.6 * temperature  # m/s
            adjusted_distance = measured_distance_cm * (speed_of_sound_actual / 343.0)

        Example:
            adjusted = UltraSonic.adjust_measurement_based_on_temp(25.0, 100.0)
            print(f"Adjusted distance: {adjusted:.1f} cm")
        """
        speed_of_sound_actual = 331.3 + 0.6 * temperature_c
        adjusted_distance = measured_distance_cm * (speed_of_sound_actual / 343.0)
        # Floor to one decimal place
        adjusted_distance = int(adjusted_distance * 10) / 10
        return adjusted_distance