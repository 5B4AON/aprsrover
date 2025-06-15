"""
compass.py

Provides a modular, testable interface for reading heading (magnetic north) from an HMC5883L digital compass sensor.

Features:
- Safe, validated access to compass heading data.
- Dependency injection for the backend, allowing testing with mock/dummy objects.
- Raises CompassError if reading fails or if no backend is injected.
- Both synchronous and asynchronous APIs for reading and monitoring.
- Suitable for import and use in other scripts or applications.
- Fully documented and suitable for unit testing.

Requires:
- Python 3.10+
- smbus2 (for I2C communication)
- HMC5883L sensor

Usage example:

    from aprsrover.compass import Compass, CompassError
    
    compass = Compass()
    heading = compass.read()
    print(f"Heading: {heading} degrees")

    # For testing or on non-hardware platforms:
    class DummyCompassBackend:
        def read(self): return 123.4
    compass = Compass(backend=DummyCompassBackend())
    print(compass.read())

    # Asynchronous monitoring:
    import asyncio
    async def print_headings():
        async for heading in compass.monitor_async(interval=2.0):
            print(f"Async: {heading} degrees")
    # asyncio.run(print_headings())

"""

from typing import Optional, Protocol, Iterator, AsyncIterator
import threading
import asyncio

class CompassError(Exception):
    """Custom exception for compass sensor errors."""
    pass

class CompassBackend(Protocol):
    def read(self) -> float:
        ...

class Compass:
    """
    HMC5883L compass sensor interface for reading heading (degrees).

    Args:
        backend: Optional backend for testing/mocking.
    """
    def __init__(self, backend: Optional[CompassBackend] = None) -> None:
        self._backend = backend
        if backend is None:
            try:
                import smbus2
                self._smbus2 = smbus2
            except ImportError as e:
                raise CompassError("smbus2 library is required for hardware access.") from e
        else:
            self._smbus2 = None

    def read(self) -> float:
        """
        Read heading from the compass sensor.
        Returns:
            heading_degrees (float)
        Raises:
            CompassError: If reading fails.
        """
        if self._backend:
            return self._backend.read()
        if not self._smbus2:
            raise CompassError("No backend or smbus2 available.")
        # Hardware implementation for HMC5883L
        try:
            bus = self._smbus2.SMBus(1)
            address = 0x1E
            # Configuration for continuous measurement mode
            bus.write_byte_data(address, 0x02, 0x00)
            data = bus.read_i2c_block_data(address, 0x03, 6)
            x = (data[0] << 8) | data[1]
            z = (data[2] << 8) | data[3]
            y = (data[4] << 8) | data[5]
            # Convert to signed
            x = x - 65536 if x > 32767 else x
            y = y - 65536 if y > 32767 else y
            heading = (180 * (self._smbus2.math.atan2(y, x)) / 3.14159265)
            if heading < 0:
                heading += 360
            return float(heading)
        except Exception as e:
            raise CompassError(f"Failed to read from HMC5883L: {e}")

    def monitor(self, interval: float = 2.0) -> Iterator[float]:
        """
        Synchronously monitor heading in a loop.
        Args:
            interval: Time in seconds between reads.
        Yields:
            heading_degrees (float)
        """
        while True:
            yield self.read()
            threading.Event().wait(interval)

    async def monitor_async(self, interval: float = 2.0) -> AsyncIterator[float]:
        """
        Asynchronously monitor heading in a loop.
        Args:
            interval: Time in seconds between reads.
        Yields:
            heading_degrees (float)
        """
        while True:
            yield self.read()
            await asyncio.sleep(interval)

class DummyCompassBackend(CompassBackend):
    """
    Dummy backend for compass sensor, for testing and development.
    All methods return fixed values and print actions to the console.
    """
    def read(self) -> float:
        print("DummyCompassBackend.read() called")
        return 123.4
