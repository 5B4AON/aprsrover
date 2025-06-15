"""
dht.py

Provides a modular, testable interface for reading temperature and humidity from DHT sensors (DHT11, DHT22, AM2302) using the Adafruit_DHT library.

Features:
- Safe, validated access to DHT sensor data.
- Dependency injection for the backend, allowing testing with mock/dummy objects.
- Raises DHTError if reading fails or if no backend is injected.
- Both synchronous and asynchronous APIs for reading and monitoring.
- Suitable for import and use in other scripts or applications.
- Fully documented and suitable for unit testing.

Requires:
- Python 3.10+
- Adafruit_DHT

Usage example:

    from aprsrover.dht import DHT, DHTError
    
    dht = DHT(sensor_type='DHT22', pin=4)
    temp, humidity = dht.read()
    print(f"Temp: {temp} C, Humidity: {humidity} %")

    # For testing or on non-hardware platforms:
    class DummyDHTBackend:
        def read(self): return (22.5, 55.0)
    dht = DHT(sensor_type='DHT22', pin=4, backend=DummyDHTBackend())
    print(dht.read())

    # Asynchronous monitoring:
    import asyncio
    async def print_readings():
        async for temp, humidity in dht.monitor_async(interval=2.0):
            print(f"Async: {temp} C, {humidity} %")
    # asyncio.run(print_readings())

"""

from typing import Optional, Protocol, Tuple, Iterator, AsyncIterator
import threading
import asyncio

class DHTError(Exception):
    """Custom exception for DHT sensor errors."""
    pass

class DHTBackend(Protocol):
    def read(self) -> Tuple[float, float]:
        ...

class DHT:
    """
    DHT sensor interface for reading temperature and humidity.

    Args:
        sensor_type: DHT sensor type ('DHT11', 'DHT22', 'AM2302').
        pin: GPIO pin number.
        backend: Optional backend for testing/mocking.
    """
    def __init__(self, sensor_type: str, pin: int, backend: Optional[DHTBackend] = None) -> None:
        self.sensor_type = sensor_type
        self.pin = pin
        self._backend = backend
        if backend is None:
            try:
                import Adafruit_DHT
                self._adafruit = Adafruit_DHT
            except ImportError as e:
                raise DHTError("Adafruit_DHT library is required for hardware access.") from e
        else:
            self._adafruit = None

    def read(self) -> Tuple[float, float]:
        """
        Read temperature and humidity from the sensor.
        Returns:
            (temperature_celsius, humidity_percent)
        Raises:
            DHTError: If reading fails.
        """
        if self._backend:
            return self._backend.read()
        if not self._adafruit:
            raise DHTError("No backend or Adafruit_DHT available.")
        sensor_map = {
            'DHT11': self._adafruit.DHT11,
            'DHT22': self._adafruit.DHT22,
            'AM2302': self._adafruit.AM2302,
        }
        sensor = sensor_map.get(self.sensor_type)
        if sensor is None:
            raise DHTError(f"Unknown sensor type: {self.sensor_type}")
        humidity, temperature = self._adafruit.read_retry(sensor, self.pin)
        if humidity is None or temperature is None:
            raise DHTError("Failed to read from DHT sensor.")
        return float(temperature), float(humidity)

    def monitor(self, interval: float = 2.0) -> Iterator[Tuple[float, float]]:
        """
        Synchronously monitor temperature and humidity in a loop.
        Args:
            interval: Time in seconds between reads.
        Yields:
            (temperature_celsius, humidity_percent)
        """
        while True:
            yield self.read()
            threading.Event().wait(interval)

    async def monitor_async(self, interval: float = 2.0) -> AsyncIterator[Tuple[float, float]]:
        """
        Asynchronously monitor temperature and humidity in a loop.
        Args:
            interval: Time in seconds between reads.
        Yields:
            (temperature_celsius, humidity_percent)
        """
        while True:
            yield self.read()
            await asyncio.sleep(interval)

class DummyDHTBackend(DHTBackend):
    """
    Dummy backend for DHT sensor, for testing and development.
    All methods return fixed values and print actions to the console.
    """
    def read(self) -> Tuple[float, float]:
        print("DummyDHTBackend.read() called")
        return (22.5, 55.0)
