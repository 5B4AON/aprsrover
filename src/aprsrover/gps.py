"""
gps.py

Provides a modular, testable interface for accessing GPS data via gpsd.
Supports both real gpsd connections and dummy/mock GPS sources for testing.

Features:

- Modular GPS access via a dependency-injected interface.
- Allows use of real gpsd or a dummy/mock for testing or non-hardware platforms.
- Methods to retrieve GPS data in DMM (degrees and decimal minutes) or decimal format.
- Input validation and robust error handling with custom exceptions.
- Suitable for use in asynchronous or multi-threaded applications.

Requires:

- Python 3.10+
- gpsd-py3

Usage example:

    from aprsrover.gps import GPS, GPSDInterface

    gps = GPS()  # Uses default gpsd client
    data = gps.get_gps_data_dmm()

    # For testing:
    class DummyGPSD(GPSDInterface):
        def get_current(self):
            class Packet:
                lat = 51.5
                lon = -0.1
                time = "2024-01-01T12:00:00.000Z"
                mode = 3
                track = 123.4
            return Packet()
    gps = GPS(gpsd=DummyGPSD())
    data = gps.get_gps_data_dmm()
"""

from typing import Optional, Protocol, Any, Tuple
from datetime import datetime
import time

__all__ = ["GPS", "GPSError", "GPSDInterface"]


class GPSError(Exception):
    """Custom exception for GPS-related errors."""
    pass


class GPSDInterface(Protocol):
    """
    Protocol for gpsd-like objects to allow dependency injection and testing.

    Implementations must provide a `get_current()` method that returns an object
    with at least the attributes: lat, lon, time, mode, track.
    """
    def get_current(self) -> Any:
        ...


class GPS:
    """
    Provides access to GPS data via gpsd or a compatible injected interface.

    Args:
        gpsd (Optional[GPSDInterface]): Optional gpsd-like object for dependency injection/testing.

    Raises:
        GPSError: If gpsd is not available and no gpsd-like object is injected.

    Example:
        gps = GPS()
        lat, lon, time, track = gps.get_gps_data_dmm()
    """
    def __init__(self, gpsd: Optional[GPSDInterface] = None) -> None:
        """
        Initialize the GPS interface.

        Parameters
        ----------
        gpsd : Optional[GPSDInterface]
            An optional gpsd-like object for dependency injection or testing.
            If not provided, attempts to use the real gpsd library.

        Raises
        ------
        GPSError
            If gpsd is not available and no gpsd-like object is injected.
        """
        if gpsd is not None:
            self.gpsd = gpsd
        else:
            try:
                import gpsd
                gpsd.connect()
                self.gpsd = gpsd
            except Exception as exc:
                raise GPSError(f"Failed to connect to gpsd: {exc}")

    def get_gps_data_dmm(
        self, max_attempts: int = 3, sleep_seconds: float = 1.0
    ) -> Optional[Tuple[str, str, str, str]]:
        """
        Returns GPS data in DMM (degrees and decimal minutes) format.

        Parameters
        ----------
        max_attempts : int
            Number of attempts to retrieve valid GPS data.
        sleep_seconds : float
            Seconds to wait between attempts.

        Returns
        -------
        Optional[Tuple[str, str, str, str]]
            Tuple of (lat_dmm, lon_dmm, tm_ddhhmmz, bearing) if successful, else None.

        Raises
        ------
        GPSError
            If an exception occurs during GPS data retrieval.

        Example
        -------
            gps = GPS()
            lat, lon, time, track = gps.get_gps_data_dmm()
        """
        exception_occurred = None

        for _ in range(max_attempts):
            try:
                packet = self.gpsd.get_current()
                latitude = packet.lat
                longitude = packet.lon
                tm = packet.time
                track = packet.track
                if packet.mode >= 2: # Values: 0=no mode value yet seen, 1=no fix, 2=2D fix, 3=3D fix
                    lat_dmm = self.decimal_to_dmm(latitude, is_latitude=True)
                    lon_dmm = self.decimal_to_dmm(longitude, is_latitude=False)
                    tm_ddhhmmz = self.iso_to_ddhhmmz(tm)
                    bearing = self.normalize_bearing(track)
                    return (lat_dmm, lon_dmm, tm_ddhhmmz, bearing)
                time.sleep(sleep_seconds)
            except Exception as exc:
                exception_occurred = exc
                break

        if exception_occurred:
            raise GPSError(
                f"Exception occurred during GPS data retrieval: {exception_occurred}"
            )
        return None

    def get_gps_data_decimal(
        self, max_attempts: int = 3, sleep_seconds: float = 1.0
    ) -> Optional[Tuple[float, float, str, float]]:
        """
        Returns GPS data in decimal degrees format.

        Args:
            max_attempts: Number of attempts to retrieve valid GPS data.
            sleep_seconds: Seconds to wait between attempts.

        Returns:
            Tuple of (lat_dec, lon_dec, tm_iso, bearing) if successful, else None.

        Raises:
            GPSError: If an exception occurs during GPS data retrieval.

        Example:
            gps = GPS()
            lat, lon, time, track = gps.get_gps_data_decimal()
        """

        exception_occurred = None

        for _ in range(max_attempts):
            try:
                packet = self.gpsd.get_current()
                latitude = packet.lat
                longitude = packet.lon
                tm = packet.time
                track = packet.track
                if packet.mode >= 2: # Values: 0=no mode value yet seen, 1=no fix, 2=2D fix, 3=3D fix
                    return (latitude, longitude, tm, float(track))
                time.sleep(sleep_seconds)
            except Exception as exc:
                exception_occurred = exc
                break

        if exception_occurred:
            raise GPSError(
                f"Exception occurred during GPS data retrieval: {exception_occurred}"
            )
        return None

    @staticmethod
    def decimal_to_dmm(coord: float, is_latitude: bool = True) -> str:
        """
        Converts a decimal degree coordinate to degrees and decimal minutes (DMM) format.

        Parameters
        ----------
        coord : float
            The coordinate in decimal degrees.
        is_latitude : bool, optional
            True if latitude, False if longitude (default is True).

        Returns
        -------
        str
            The coordinate in DMM format with direction.
        """
        degrees = int(abs(coord))
        minutes = (abs(coord) - degrees) * 60
        if is_latitude:
            dmm = f"{degrees:02d}{minutes:05.2f}"
            direction = "N" if coord >= 0 else "S"
        else:
            dmm = f"{degrees:03d}{minutes:05.2f}"
            direction = "E" if coord >= 0 else "W"
        return f"{dmm}{direction}"

    @staticmethod
    def iso_to_ddhhmmz(iso_time: str) -> str:
        """
        Converts an ISO timestamp to APRS DDHHMMz format.

        Parameters
        ----------
        iso_time : str
            The ISO formatted time string.

        Returns
        -------
        str
            The time in DDHHMMz format.
        """
        dt = datetime.strptime(iso_time, "%Y-%m-%dT%H:%M:%S.%fZ")
        return dt.strftime("%d%H%Mz")

    @staticmethod
    def normalize_bearing(track: float) -> str:
        """
        Normalizes a bearing value to a 3-digit string (000-360).

        Parameters
        ----------
        track : float
            The bearing value in degrees.

        Returns
        -------
        str
            The bearing as a zero-padded 3-digit string.
        """
        bearing_int = int(round(track)) % 360
        return f"{bearing_int:03d}"
