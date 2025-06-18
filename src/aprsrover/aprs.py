"""
aprs.py - APRS KISS TNC interface and observer utilities

This module provides the Aprs class for interacting with a KISS TNC (Terminal Node Controller)
using the AX.25 protocol for APRS (Automatic Packet Reporting System) messaging. It supports:

Features:

- Connecting to a KISS TNC over TCP (async, must be awaited)
- Sending APRS messages, object reports and position reports with parameter validation
- Registering and managing observer callbacks for incoming frames, filtered by callsign
- Utility methods for extracting messages addressed to a specific callsign
- Acknowledging received APRS messages
- **Dependency injection:** Allows injection of a custom KISS interface for testing or simulation

Requires:

- Python 3.10+
- kiss3
- ax253

Usage example:

    import asyncio
    from aprsrover.aprs import Aprs

    def my_frame_handler(frame):
        print("Received frame:", frame)

    async def main():
        aprs = Aprs(host="localhost", port=8001)
        await aprs.connect()
        aprs.register_observer("5B4AON-9", my_frame_handler)
        # Keep the event loop running to receive frames
        await aprs.run()

    asyncio.run(main())

Testing with a DummyKISS interface:

    from aprsrover.aprs import Aprs, KISSInterface

    class DummyKISS(KISSInterface):
        async def create_tcp_connection(self, host, port, kiss_settings):
            class DummyProtocol:
                def write(self, frame): print("Dummy write:", frame)
                async def read(self):
                    yield None  # Simulate no frames
            return (None, DummyProtocol())
        def write(self, frame): print("Dummy write:", frame)
        def read(self): yield None

    aprs = Aprs(kiss=DummyKISS())
    # Now you can call aprs.send_my_message_no_ack(...) etc. for unit testing without hardware.

See the README.md for more usage examples and parameter details.

This module is designed to be imported and used from other Python scripts.
"""

from typing import AsyncGenerator, Optional, Callable, Awaitable, Protocol, Any
from ax253 import Frame
import logging
import asyncio
import re

__all__ = ["Aprs", "AprsError", "KISSInterface"]


class AprsError(Exception):
    """Custom exception for APRS-related errors."""
    pass


class KISSInterface(Protocol):
    """
    Protocol for KISS TNC interface to allow dependency injection and testing.

    Implementations must provide:
    - async create_tcp_connection(host: str, port: int, kiss_settings: dict) -> (Any, Any)
    - Frame reading via an async iterator (yielding Frame objects)
    - write(frame: Frame) -> None
    """
    async def create_tcp_connection(self, host: str, port: int, kiss_settings: dict) -> tuple[Any, Any]:
        ...

    def write(self, frame: Frame) -> None:
        ...

    def read(self) -> AsyncGenerator[Frame, Any]:
        ...


class Aprs:
    """
    APRS KISS TNC interface supporting observer pattern for frame reception.

    Note:
        - The `connect()` and `run()` methods are asynchronous and must be awaited.
        - Call `await run()` after connecting to start receiving frames and notifying observers.
        - You can inject a custom KISS interface for testing or simulation.
    """

    KISS_DEFAULT_HOST = "localhost"
    KISS_DEFAULT_PORT = 8001

    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        kiss: Optional[KISSInterface] = None,
    ) -> None:
        """
        Initialize the KISS protocol settings.

        Args:
            host: Hostname or IP address of the KISS TNC.
            port: TCP port of the KISS TNC.
            kiss: Optional KISSInterface instance for dependency injection/testing.
        """
        self.APRS_SW_VERSION = "APDW16"  # DireWolf version
        self.host = host or self.KISS_DEFAULT_HOST
        self.port = port or self.KISS_DEFAULT_PORT
        self.transport = None
        self.kiss_protocol = None
        self.settings = None
        self.initialized = False
        self._observers: dict[str, list[Callable[[Frame], None]]] = {}
        self._run_task: Optional[asyncio.Task] = None

        if kiss is not None:
            self.kiss = kiss
            # Use dummy settings if not present
            self.settings = getattr(kiss, "settings", {0x01: 50, 0x02: 10})
        else:
            import kiss
            self.kiss = kiss
            self.settings = {kiss.Command.TX_DELAY: 50, kiss.Command.TX_TAIL: 10}

    async def connect(self) -> None:
        """
        Establish TCP connection to the KISS TNC.

        Raises:
            AprsError: If connection fails.
        """
        try:
            self.transport, self.kiss_protocol = await self.kiss.create_tcp_connection(
                host=self.host, port=self.port, kiss_settings=self.settings
            )
            self.initialized = True
            logging.info(f"Connected to KISS TNC at {self.host}:{self.port}")
        except Exception as e:
            self.initialized = False
            logging.error(f"Failed to connect to KISS TNC: {e}")
            raise AprsError(f"Failed to connect to KISS TNC: {e}")

    async def run(self) -> None:
        """
        Start an infinite async loop to read frames and notify observers.

        This method must be awaited and will run until cancelled.
        """
        if not self.initialized or self.kiss_protocol is None:
            raise AprsError("KISS protocol not initialized. Call connect() first.")
        try:
            async for frame in self.kiss_protocol.read():
                self._notify_observers(frame)
        except asyncio.CancelledError:
            logging.info("APRS run loop cancelled.")
        except Exception as e:
            logging.error(f"Error in APRS run loop: {e}")
            raise AprsError(f"Error in APRS run loop: {e}")

    def register_observer(self, mycall: str, callback: Callable[[Frame], None]) -> None:
        """
        Register a callback to be called when a frame arrives for a specific callsign.

        Args:
            mycall: The observer's callsign.
            callback: A function that accepts a single argument (the frame).
        """
        if not isinstance(mycall, str) or not mycall:
            raise ValueError("mycall must be a non-empty string.")
        if not callable(callback):
            raise ValueError("callback must be callable.")
        if mycall not in self._observers:
            self._observers[mycall] = []
        if callback not in self._observers[mycall]:
            self._observers[mycall].append(callback)

    def unregister_observer(
        self, mycall: str, callback: Optional[Callable[[Frame], None]] = None
    ) -> None:
        """
        Unregister a callback or all callbacks for a specific callsign.

        Args:
            mycall: The observer's callsign.
            callback: The callback function to remove. If None, remove all callbacks for this callsign.
        """
        if mycall in self._observers:
            if callback is None:
                del self._observers[mycall]
            else:
                try:
                    self._observers[mycall].remove(callback)
                    if not self._observers[mycall]:
                        del self._observers[mycall]
                except ValueError:
                    pass  # Callback not found; ignore

    def clear_observers(self) -> None:
        """
        Clear all registered observers.
        """
        self._observers.clear()

    def _notify_observers(self, frame: Frame) -> None:
        """
        Internal method to notify all registered observers of a new frame.
        Only notifies observers whose callsign appears in the frame.

        Args:
            frame: The received frame.
        """
        info = frame.info.decode("UTF-8")
        logging.debug(frame)
        for callsign, callbacks in self._observers.items():
            logging.debug(f"Looking for callsign:{callsign}")
            if f":{callsign.ljust(9)}:" in info:
                logging.debug(f"Invoking callbacks for: {callsign}")
                for callback in callbacks:
                    try:
                        callback(frame)
                    except Exception as e:
                        logging.error(f"Observer callback error for {callsign}: {e}")

    @staticmethod
    def get_my_message(callsign: str, frame: Frame) -> Optional[str]:
        """
        Extract the message if it is addressed to my callsign.

        Args:
            frame: The KISS frame to extract the message from.

        Returns:
            str: The message if found, otherwise None.
        """
        info = frame.info.decode("UTF-8")
        if f":{callsign}" in info:
            message: str = info[info.index(f":{callsign}".ljust(10) + ":") + 11 :]
            if "{" in message:
                message = message[0 : message.index("{")]
            return message.strip()
        return None

    def send_my_message_no_ack(
        self, mycall: str, path: list[str], recipient: str, message: str
    ) -> None:
        """
        Send an APRS message via the KISS TNC without requesting an acknowledgement.

        Args:
            mycall: My callsign (3-6 uppercase alphanumeric characters, then '-', then 1-2 digits).
            path: The digipeater path as a list of strings.
            recipient: The recipient callsign (same format as mycall).
            message: The message text to send (1 to 67 characters).

        Raises:
            AprsError: If the KISS protocol is not initialized or sending fails.
            ValueError: If any parameter is invalid.
        """
        if not self.initialized:
            logging.error("Cannot send message: KISS protocol not initialized.")
            raise AprsError("KISS protocol not initialized.")

        # Use helper validation functions
        self._validate_callsign(mycall, "mycall")
        self._validate_callsign(recipient, "recipient")
        self._validate_path(path)

        # Validate message
        if not isinstance(message, str) or not (1 <= len(message) <= 67):
            logging.error(
                "Message must be a non-empty string of 1 to 67 characters. Got length: %d",
                len(message) if isinstance(message, str) else -1,
            )
            raise ValueError("Message must be a non-empty string of 1 to 67 characters.")

        info = f":{recipient}".ljust(10) + f":{message}"
        try:
            frame = Frame.ui(
                destination=self.APRS_SW_VERSION,
                source=mycall,
                path=path,
                info=info.encode("utf-8"),
            )
            if self.kiss_protocol is None:
                raise AprsError("KISS protocol not initialized. Call connect() first.")
            self.kiss_protocol.write(frame)
            logging.info(f"Sent APRS message from {mycall} to {recipient}: {message}")
        except Exception as e:
            logging.error(f"Failed to send APRS message: {e}")
            raise AprsError(f"Failed to send APRS message: {e}")

    def _validate_callsign(self, callsign: str, param_name: str = "callsign") -> None:
        """Validate APRS callsign format."""
        callsign_pattern = re.compile(r"^[A-Z0-9]{3,6}-\d{1,2}$")
        if not callsign_pattern.match(callsign) or len(callsign) > 9:
            logging.error(
                "%s must be 3-6 uppercase alphanumeric characters, a dash, then 1-2 digits (max 9 chars). Got: %r",
                param_name,
                callsign,
            )
            raise ValueError(
                f"{param_name} must be 3-6 uppercase alphanumeric characters, a dash, then 1-2 digits (max 9 chars)."
            )

    def _validate_path(self, path: list[str]) -> None:
        """Validate APRS path format."""
        if not isinstance(path, list) or not all(isinstance(p, str) and p for p in path):
            logging.error("path must be a list of non-empty strings. Got: %r", path)
            raise ValueError("path must be a list of non-empty strings.")

    def _validate_time_dhm(
        self, time_dhm: Optional[str], param_name: str = "time_dhm", required: bool = False
    ) -> None:
        """Validate DHM time string if provided or required."""
        if time_dhm is None:
            if required:
                logging.error("%s is required.", param_name)
                raise ValueError(f"{param_name} is required.")
            return  # Optional and not provided, so valid

        if (
            not isinstance(time_dhm, str)
            or len(time_dhm) != 7
            or not time_dhm[:6].isdigit()
            or time_dhm[-1] != "z"
        ):
            logging.error(
                "%s must be a 6-digit string followed by 'z'. Got: %r",
                param_name,
                time_dhm,
            )
            raise ValueError(
                f"{param_name} must be a 6-digit string followed by 'z' (e.g., '011234z')."
            )

    def _validate_lat_dmm(self, lat_dmm: str) -> None:
        """Validate latitude in DMM format."""
        if (
            not isinstance(lat_dmm, str)
            or len(lat_dmm) < 8 # e.g. 5132.07N
            or not lat_dmm[:-1].replace(".", "", 1).isdigit()
            or lat_dmm[-1] not in "NS"
        ):
            logging.error("lat_dmm must be in DMM format ending with N or S. Got: %r", lat_dmm)
            raise ValueError(
                "lat_dmm must be 7 digits (with optional dot) followed by N or S (e.g., '5132.07N')."
            )

    def _validate_long_dmm(self, long_dmm: str) -> None:
        """Validate longitude in DMM format."""
        if (
            not isinstance(long_dmm, str)
            or len(long_dmm) < 8 # e.g. 00007.40W
            or not long_dmm[:-1].replace(".", "", 1).isdigit()
            or long_dmm[-1] not in "EW"
        ):
            logging.error("long_dmm must be in DMM format ending with E or W. Got: %r", long_dmm)
            raise ValueError("long_dmm must be in DMM format ending with E or W.")

    def _validate_symbol(self, symbol: str, param_name: str) -> None:
        """Validate symbol ID or code (single character)."""
        if not isinstance(symbol, str) or len(symbol) != 1:
            logging.error("%s must be a single character. Got: %r", param_name, symbol)
            raise ValueError(f"{param_name} must be a single character.")

    def _validate_comment(self, comment: str, max_len: int = 43) -> None:
        """Validate comment string."""
        if not isinstance(comment, str) or not (0 <= len(comment) <= max_len):
            logging.error(
                "comment must be a string of 0 to %d characters. Got length: %d",
                max_len,
                len(comment) if isinstance(comment, str) else -1,
            )
            raise ValueError(f"comment must be a string of 0 to {max_len} characters.")

    def send_object_report(
        self,
        mycall: str,
        path: list[str],
        time_dhm: str,
        lat_dmm: str,
        long_dmm: str,
        symbol_id: str,
        symbol_code: str,
        comment: str,
        name: Optional[str] = None,
    ) -> None:
        """
        Sends an APRS object report.

        Args:
            mycall: My callsign (3-6 uppercase alphanumeric characters, then '-', then 1-2 digits, max 9 chars).
            path: The digipeater path as a list of strings.
            time_dhm: The time in DHM format (6 digits followed by 'z', e.g., '011234z').
            lat_dmm: The latitude in DMM format (7 digits + N/S, e.g., '5132.07N').
            long_dmm: The longitude in DMM format (e.g., '00007.40W').
            symbol_id: The symbol ID (1 character).
            symbol_code: The symbol code (1 character).
            comment: The comment field (43 characters). May contain any appropriate APRS data, such as free text, course, speed, telemetry, or other APRS-compatible extensions.
            name: Optional object name (up to 9 characters). If not provided, uses `mycall`.

        Raises:
            AprsError: If the KISS protocol is not initialized or sending fails.
            ValueError: If any parameter is invalid.
        """
        if not self.initialized:
            logging.error("Cannot send object: KISS protocol not initialized.")
            raise AprsError("KISS protocol not initialized.")

        self._validate_callsign(mycall, "mycall")
        self._validate_path(path)
        self._validate_time_dhm(time_dhm, required=True)
        self._validate_lat_dmm(lat_dmm)
        self._validate_long_dmm(long_dmm)
        self._validate_symbol(symbol_id, "symbol_id")
        self._validate_symbol(symbol_code, "symbol_code")
        self._validate_comment(comment)

        # Validate name (object name)
        obj_name = name if name is not None else mycall
        if not isinstance(obj_name, str) or not (1 <= len(obj_name) <= 9):
            logging.error(
                "Object name must be a string of 1 to 9 characters. Got: %r", obj_name
            )
            raise ValueError("Object name must be a string of 1 to 9 characters.")
        # Pad object name to 9 characters for the frame
        obj_name_padded = obj_name.ljust(9)

        # Build info field
        info = (
            f";{obj_name_padded}*{time_dhm}{lat_dmm}{symbol_id}{long_dmm}{symbol_code}{comment}"
        )
        try:
            frame = Frame.ui(
                destination=self.APRS_SW_VERSION, # Typically APRS software version or generic ID
                source=mycall,
                path=path,
                info=info.encode("utf-8"),
            )
            if self.kiss_protocol is None:
                raise AprsError("KISS protocol not initialized. Call connect() first.")
            self.kiss_protocol.write(frame)
            logging.info(f"Sent APRS object: {info}")
        except Exception as e:
            logging.error(f"Failed to send APRS object: {e}")
            raise AprsError(f"Failed to send APRS object: {e}")

    def send_ack_if_requested(self, frame: Frame, mycall: str, path: list[str]) -> None:
        """
        Send an APRS acknowledgment for the received frame if an ack is requested.

        Args:
            frame: The KISS frame to acknowledge.
            mycall: The sender's callsign.
            path: The digipeater path as a list of strings.
        """
        try:
            if self.initialized and self.kiss_protocol is not None:
                info = frame.info.decode("UTF-8")
                if "{" in info:
                    ack = info[info.index("{") + 1 :].strip()
                    # Only take up to the next space or end of string
                    ack = ack.split()[0] if ack else ""
                    ack_info = f":{frame.source}".ljust(10) + f":ack{ack}"
                    logging.debug(f"Sending acknowledgment: {ack_info}")
                    self.kiss_protocol.write(
                        Frame.ui(
                            destination="APDR16",
                            source=mycall,
                            path=path,
                            info=ack_info.encode(),
                        )
                    )
        except Exception as e:
            logging.error(f"Failed to send APRS acknowledgment: {e}")

    def send_position_report(
        self,
        mycall: str,
        path: list[str],
        lat: float | str,
        lon: float | str,
        symbol_id: str,
        symbol_code: str,
        comment: str,
        time_dhm: Optional[str] = None,
        compressed: bool = False,
    ) -> None:
        """
        Sends an APRS position report (standard or compressed).

        Args:
            mycall: My callsign (3-6 uppercase alphanumeric characters, then '-', then 1-2 digits, max 9 chars).
            path: The digipeater path as a list of strings.
            lat: Latitude (float in decimal degrees if compressed, else DMM string).
            lon: Longitude (float in decimal degrees if compressed, else DMM string).
            symbol_id: The symbol ID (1 character).
            symbol_code: The symbol code (1 character).
            comment: The comment field (43 characters).
            time_dhm: Optional time in DHM format (6 digits followed by 'z', e.g., '011234z').
            compressed: If True, use APRS compressed position format.

        Raises:
            AprsError: If the KISS protocol is not initialized or sending fails.
            ValueError: If any parameter is invalid.
        """
        if not self.initialized:
            logging.error("Cannot send position: KISS protocol not initialized.")
            raise AprsError("KISS protocol not initialized.")

        self._validate_callsign(mycall, "mycall")
        self._validate_path(path)
        self._validate_symbol(symbol_id, "symbol_id")
        self._validate_symbol(symbol_code, "symbol_code")
        self._validate_comment(comment)
        self._validate_time_dhm(time_dhm, required=False)

        if compressed:
            if not (isinstance(lat, float) and isinstance(lon, float)):
                raise ValueError("lat and lon must be float when using compressed format.")

            def to_base91(val: int) -> str:
                # Returns a 1-character base91 string for 0 <= val < 91
                return chr(val + 33)

            def encode_compressed(lat: float, lon: float) -> tuple[str, str]:
                # See APRS spec for details
                y = int(round(380926 * (90 - lat)))
                x = int(round(190463 * (180 + lon)))
                lat_enc = ""
                lon_enc = ""
                for i in range(4):
                    lat_enc = to_base91(y % 91) + lat_enc
                    y //= 91
                    lon_enc = to_base91(x % 91) + lon_enc
                    x //= 91
                return lat_enc, lon_enc

            lat_enc, lon_enc = encode_compressed(lat, lon)
            # Altitude, course, speed, and other extensions can be encoded here if needed
            # For now, fill with ' ' (space) for no extension
            ext = "   "
            if time_dhm:
                info = f"/{time_dhm}{symbol_id}{lat_enc}{lon_enc}{symbol_code}{ext}{comment}"
            else:
                info = f"!{symbol_id}{lat_enc}{lon_enc}{symbol_code}{ext}{comment}"
        else:
            # Standard format: lat/lon as DMM strings
            self._validate_lat_dmm(lat)  # type: ignore
            self._validate_long_dmm(lon)  # type: ignore
            if time_dhm:
                info = f"/{time_dhm}{lat}{symbol_id}{lon}{symbol_code}{comment}"
            else:
                info = f"!{lat}{symbol_id}{lon}{symbol_code}{comment}"

        try:
            frame = Frame.ui(
                destination=self.APRS_SW_VERSION,
                source=mycall,
                path=path,
                info=info.encode("utf-8"),
            )
            if self.kiss_protocol is None:
                raise AprsError("KISS protocol not initialized. Call connect() first.")
            self.kiss_protocol.write(frame)
            logging.info(
                "Sent APRS position report from %s: %s", mycall, info
            )
        except Exception as e:
            logging.error("Failed to send APRS position report: %s", e)
            raise AprsError(f"Failed to send APRS position report: {e}") from e

    def send_status_report(
        self,
        mycall: str,
        path: list[str],
        status: str,
        time_dhm: Optional[str] = None,
    ) -> None:
        """
        Send an APRS Status Report (Data Type Identifier '>').

        Args:
            mycall: My callsign (3-6 uppercase alphanumeric characters, then '-', then 1-2 digits, max 9 chars).
            path: The digipeater path as a list of strings.
            status: The status text (up to 62 chars without timestamp, or 55 chars with timestamp).
                May contain any printable ASCII except | or ~.
            time_dhm: Optional timestamp in DHM zulu format (6 digits + 'z', e.g., '092345z').

        Raises:
            AprsError: If the KISS protocol is not initialized or sending fails.
            ValueError: If any parameter is invalid.

        Example:
            aprs.send_status_report(
                mycall="5B4AON-9",
                path=["WIDE1-1"],
                status="Net Control Center",
                time_dhm="092345z"
            )
        """
        if not self.initialized:
            logging.error("Cannot send status: KISS protocol not initialized.")
            raise AprsError("KISS protocol not initialized.")

        self._validate_callsign(mycall, "mycall")
        self._validate_path(path)
        self._validate_time_dhm(time_dhm, required=False)

        # Validate status text
        max_status_len = 55 if time_dhm else 62
        if not isinstance(status, str) or not (1 <= len(status) <= max_status_len):
            logging.error(
                "status must be a string of 1 to %d characters. Got length: %d",
                max_status_len,
                len(status) if isinstance(status, str) else -1,
            )
            raise ValueError(
                f"status must be a string of 1 to {max_status_len} characters."
            )
        if "|" in status or "~" in status:
            logging.error("status text cannot contain '|' or '~'. Got: %r", status)
            raise ValueError("status text cannot contain '|' or '~'.")


        # Build info field
        if time_dhm:
            info = f">{time_dhm}{status}"
        else:
            info = f">{status}"

        try:
            frame = Frame.ui(
                destination=self.APRS_SW_VERSION,
                source=mycall,
                path=path,
                info=info.encode("utf-8"),
            )
            if self.kiss_protocol is None:
                raise AprsError("KISS protocol not initialized. Call connect() first.")
            self.kiss_protocol.write(frame)
            logging.info("Sent APRS status report from %s: %s", mycall, info)
        except Exception as e:
            logging.error("Failed to send APRS status report: %s", e)
            raise AprsError(f"Failed to send APRS status report: {e}") from e