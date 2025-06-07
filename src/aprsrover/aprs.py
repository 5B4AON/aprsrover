"""
aprs.py - APRS KISS TNC interface and observer utilities

This module provides the Aprs class for interacting with a KISS TNC (Terminal Node Controller)
using the AX.25 protocol for APRS (Automatic Packet Reporting System) messaging. It supports:

- Connecting to a KISS TNC over TCP (async, must be awaited)
- Sending APRS messages and objects with parameter validation
- Registering and managing observer callbacks for incoming frames, filtered by callsign
- Utility methods for extracting messages addressed to a specific callsign
- Acknowledging received APRS messages
- **Dependency injection:** Allows injection of a custom KISS interface for testing or simulation

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

Dependencies:
    - kiss3
    - ax253

This module is designed to be imported and used from other Python scripts.
"""

from typing import Optional, Callable, Awaitable, Protocol, Any
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

    def read(self):
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

        # Validate mycall and recipient
        callsign_pattern = re.compile(r"^[A-Z0-9]{3,6}-\d{1,2}$")
        for callsign, label in [(mycall, "mycall"), (recipient, "recipient")]:
            if (
                not isinstance(callsign, str)
                or not callsign_pattern.fullmatch(callsign)
                or len(callsign) > 9
            ):
                logging.error(
                    "%s must be 3-6 uppercase alphanumeric characters, a dash, then 1-2 digits (max 9 chars). Got: %r",
                    label, callsign
                )
                raise ValueError(
                    f"{label} must be 3-6 uppercase alphanumeric characters, a dash, then 1-2 digits (max 9 chars)."
                )

        # Validate path
        if not isinstance(path, list) or not all(isinstance(p, str) and p for p in path):
            logging.error("path must be a list of non-empty strings. Got: %r", path)
            raise ValueError("path must be a list of non-empty strings.")

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
            self.kiss_protocol.write(frame)
            logging.info(f"Sent APRS message from {mycall} to {recipient}: {message}")
        except Exception as e:
            logging.error(f"Failed to send APRS message: {e}")
            raise AprsError(f"Failed to send APRS message: {e}")

    def send_my_object_no_course_speed(
        self,
        mycall: str,
        path: list[str],
        time_dhm: str,
        lat_dmm: str,
        long_dmm: str,
        symbol_id: str,
        symbol_code: str,
        comment: str,
    ) -> None:
        """
        Send an APRS object with a comment, without including course and speed data.

        Args:
            mycall: My callsign (3-6 uppercase alphanumeric characters, then '-', then 1-2 digits, max 9 chars).
            path: The digipeater path as a list of strings.
            time_dhm: The time in DHM format (6 digits followed by 'z', e.g., '011234z').
            lat_dmm: The latitude in DMM format (7 digits + N/S, e.g., '5132.07N').
            long_dmm: The longitude in DMM format (e.g., '00007.40W').
            symbol_id: The symbol ID (1 character).
            symbol_code: The symbol code (1 character).
            comment: The comment text (0 to 43 characters).

        Raises:
            AprsError: If the KISS protocol is not initialized or sending fails.
            ValueError: If any parameter is invalid.
        """
        if not self.initialized:
            logging.error("Cannot send object: KISS protocol not initialized.")
            raise AprsError("KISS protocol not initialized.")

        # Validate mycall (same as other callsigns: 3-6 uppercase alphanumeric, dash, 1-2 digits, max 9 chars)
        callsign_pattern = re.compile(r"^[A-Z0-9]{3,6}-\d{1,2}$")
        if (
            not isinstance(mycall, str)
            or not callsign_pattern.fullmatch(mycall)
            or len(mycall) > 9
        ):
            logging.error(
                "mycall must be 3-6 uppercase alphanumeric characters, a dash, then 1-2 digits (max 9 chars). Got: %r",
                mycall
            )
            raise ValueError(
                "mycall must be 3-6 uppercase alphanumeric characters, a dash, then 1-2 digits (max 9 chars)."
            )

        # Validate path
        if not isinstance(path, list) or not all(isinstance(p, str) and p for p in path):
            logging.error("path must be a list of non-empty strings. Got: %r", path)
            raise ValueError("path must be a list of non-empty strings.")

        # Validate time_dhm (must be 6 digits followed by 'z')
        if (
            not isinstance(time_dhm, str)
            or len(time_dhm) != 7
            or not time_dhm[:6].isdigit()
            or time_dhm[-1] != "z"
        ):
            logging.error("time_dhm must be a 6-digit string followed by 'z'. Got: %r", time_dhm)
            raise ValueError("time_dhm must be a 6-digit string followed by 'z' (e.g., '011234z').")

        # Validate lat_dmm (must be 7 digits + N/S, e.g., '5132.07N')
        if (
            not isinstance(lat_dmm, str)
            or len(lat_dmm) != 8
            or not lat_dmm[:7].replace(".", "", 1).isdigit()
            or lat_dmm[-1] not in "NS"
        ):
            logging.error(
                "lat_dmm must be 7 digits (with optional dot) followed by N or S. Got: %r", lat_dmm
            )
            raise ValueError(
                "lat_dmm must be 7 digits (with optional dot) followed by N or S (e.g., '5132.07N')."
            )

        # Validate long_dmm
        if (
            not isinstance(long_dmm, str)
            or len(long_dmm) < 8
            or not long_dmm[:-1].replace(".", "", 1).isdigit()
            or long_dmm[-1] not in "EW"
        ):
            logging.error("long_dmm must be in DMM format ending with E or W. Got: %r", long_dmm)
            raise ValueError("long_dmm must be in DMM format ending with E or W.")

        # Validate symbol_id
        if not isinstance(symbol_id, str) or len(symbol_id) != 1:
            logging.error("symbol_id must be a single character. Got: %r", symbol_id)
            raise ValueError("symbol_id must be a single character.")

        # Validate symbol_code
        if not isinstance(symbol_code, str) or len(symbol_code) != 1:
            logging.error("symbol_code must be a single character. Got: %r", symbol_code)
            raise ValueError("symbol_code must be a single character.")

        # Validate comment
        if not isinstance(comment, str) or not (0 <= len(comment) <= 43):
            logging.error(
                "comment must be a string of 0 to 43 characters. Got length: %d",
                len(comment) if isinstance(comment, str) else -1,
            )
            raise ValueError("comment must be a string of 0 to 43 characters.")

        info = (
            f";{mycall}".ljust(10)
            + f"*{time_dhm}{lat_dmm}{symbol_id}{long_dmm}{symbol_code}{comment}"
        )
        try:
            frame = Frame.ui(
                destination=self.APRS_SW_VERSION,
                source=mycall,
                path=path,
                info=info.encode("utf-8"),
            )
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
