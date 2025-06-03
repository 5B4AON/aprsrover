"""
gps.py - GPSD interface and GPS utility functions

This module provides the GPS class for connecting to GPSD and retrieving GPS data,
as well as utility functions for coordinate and time formatting for APRS.

Features:
- Connect to GPSD and retrieve current GPS data (latitude, longitude, time, bearing)
- Retrieve GPS data in either APRS DMM format (for APRS) or decimal degrees (for calculations)
- `get_gps_data_dmm`: Returns (lat_dmm, lon_dmm, time_ddhhmmz, bearing) for APRS
- `get_gps_data_decimal`: Returns (lat_decimal, lon_decimal, iso_time, bearing) for calculations
- Convert decimal degrees to degrees and decimal minutes (DMM) format
- Convert ISO timestamps to APRS DDHHMMz format
- Normalize bearing values for APRS
- Designed for import and use in other Python scripts

Usage example:

    from aprsrover.gps import GPS, GPSError

    gps = GPS()
    try:
        gps.connect()
        # Get APRS DMM format
        data = gps.get_gps_data_dmm()
        if data is None:
            print("No GPS fix yet. Try running: cgps -s")
        else:
            lat_dmm, lon_dmm, tm, bearing = data
            # Get decimal degrees format
            print("APRS DMM:", lat_dmm, lon_dmm, tm, bearing)
    except GPSError as e:
        print(f"GPS error: {e}")

See the README.md for more usage examples and parameter details.

Dependencies:
    - gpsd-py3

This module is designed to be imported and used from other Python scripts.
"""

import gpsd
import time
from datetime import datetime
from typing import Optional, Any, Tuple

__all__ = ["GPS", "GPSError"]


class GPSError(Exception):
    """Custom exception for GPS-related errors."""
    pass


class GPS:
    """
    A class to interface with a GPS device using gpsd.

    Methods
    -------
    connect() -> None
        Connects to the local gpsd daemon.
    get_gps_data_dmm(...) -> Optional[tuple[str, str, str, str]]
        Retrieves GPS data in APRS DMM format (latitude, longitude, datetime, bearing).
    get_gps_data_decimal(...) -> Optional[tuple[float, float, str, float]]
        Retrieves GPS data in decimal degrees (latitude, longitude, ISO time, bearing).
    """

    def connect(self) -> None:
        """
        Connect to the local gpsd daemon.

        Raises:
            GPSError: If connection to gpsd fails.
        """
        self.gpsd = gpsd
        try:
            self.gpsd.connect()
        except Exception as exc:
            raise GPSError(f"Failed to connect to gpsd: {exc}") from exc

    def get_gps_data_dmm(
        self, max_attempts: int = 3, sleep_seconds: float = 1.0
    ) -> Optional[Tuple[str, str, str, str]]:
        """
        Retrieve GPS data in APRS DMM format.

        Args:
            max_attempts: Number of attempts to retrieve valid GPS data.
            sleep_seconds: Seconds to wait between attempts.

        Returns:
            Tuple of (lat_dmm, lon_dmm, tm_ddhhmmz, bearing) if successful, else None.

        Raises:
            GPSError: If an exception occurs during GPS data retrieval.
        """

        exception_occurred = None

        for _ in range(max_attempts):
            try:
                packet = self.gpsd.get_current()
                latitude = packet.lat
                longitude = packet.lon
                tm = packet.time
                track = packet.track
                if packet.mode >= 2:
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
        Retrieve GPS data in decimal degrees.

        Args:
            max_attempts: Number of attempts to retrieve valid GPS data.
            sleep_seconds: Seconds to wait between attempts.

        Returns:
            Tuple of (lat_dec, lon_dec, tm_iso, bearing) if successful, else None.

        Raises:
            GPSError: If an exception occurs during GPS data retrieval.
        """

        exception_occurred = None

        for _ in range(max_attempts):
            try:
                packet = self.gpsd.get_current()
                latitude = packet.lat
                longitude = packet.lon
                tm = packet.time
                track = packet.track
                if packet.mode >= 2:
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
