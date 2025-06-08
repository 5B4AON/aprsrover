"""
hw_info.py

Provides a modular, testable interface for querying Raspberry Pi system information such as
CPU temperature, CPU usage, RAM usage, and system uptime.

Features:
- Safe, validated access to hardware/system info.
- Dependency injection for the backend, allowing testing with mock/dummy objects.
- Raises HWInfoError if not running on Raspberry Pi and no backend is injected.
- All functions are suitable for import and use in other scripts or applications.
- Fully documented and suitable for unit testing.

Requires:
- Python 3.10+
- psutil (for CPU/RAM usage)
- Running on Raspberry Pi hardware (unless using a dummy backend)

Usage example:

    from aprsrover.hw_info import HWInfo, HWInfoError

    try:
        hw = HWInfo()
        print("CPU Temp:", hw.get_cpu_temp())
        print("CPU Usage:", hw.get_cpu_usage())
        print("RAM Usage:", hw.get_ram_usage())
        print("Uptime:", hw.get_uptime())
    except HWInfoError as e:
        print(f"Hardware info error: {e}")

    # For testing or on non-RPi platforms:
    class DummyHWInfo:
        def get_cpu_temp(self): return "42.0"
        def get_cpu_usage(self): return "10"
        def get_ram_usage(self): return "20"
        def get_uptime(self): return "00:42:00"
    hw = HWInfo(backend=DummyHWInfo())
    print(hw.get_cpu_temp())

"""

from typing import Optional, Protocol
import platform

class HWInfoError(Exception):
    """Custom exception for hardware info errors."""
    pass

class HWInfoInterface(Protocol):
    def get_cpu_temp(self) -> str: ...
    def get_cpu_usage(self) -> str: ...
    def get_ram_usage(self) -> str: ...
    def get_uptime(self) -> str: ...

class _RaspberryPiHWInfo:
    """
    Raspberry Pi system info backend.

    Provides methods to query CPU temperature, CPU usage, RAM usage, and uptime.
    """
    def __init__(self) -> None:
        try:
            import psutil  # type: ignore
        except ImportError as exc:
            raise HWInfoError("psutil is required for HWInfo on Raspberry Pi.") from exc
        self._psutil = psutil

    def get_cpu_temp(self) -> str:
        """
        Returns the CPU temperature in Celsius as a string (e.g., "48.2").

        Raises:
            HWInfoError: If unable to read the temperature.
        """
        mypath = "/sys/class/thermal/thermal_zone0/temp"
        try:
            with open(mypath, 'r') as mytmpfile:
                result = mytmpfile.readline()
            temp = float(result) / 1000
            return str(round(temp, 1))
        except Exception as exc:
            raise HWInfoError(f"Failed to read CPU temperature: {exc}")

    def get_cpu_usage(self) -> str:
        """
        Returns the CPU usage percentage as a string (e.g., "12.5").

        Raises:
            HWInfoError: If unable to read CPU usage.
        """
        try:
            cpu_cent = self._psutil.cpu_percent()
            return str(cpu_cent)
        except Exception as exc:
            raise HWInfoError(f"Failed to read CPU usage: {exc}")

    def get_ram_usage(self) -> str:
        """
        Returns the RAM usage percentage as a string (e.g., "42.0").

        Raises:
            HWInfoError: If unable to read RAM usage.
        """
        try:
            ram_cent = self._psutil.virtual_memory()[2]
            return str(ram_cent)
        except Exception as exc:
            raise HWInfoError(f"Failed to read RAM usage: {exc}")

    def get_uptime(self) -> str:
        """
        Returns the system uptime as a string in HH:MM:SS format.

        Raises:
            HWInfoError: If unable to read uptime.
        """
        try:
            with open('/proc/uptime', 'r') as f:
                uptime_seconds = float(f.readline().split()[0])
            hours = int(uptime_seconds // 3600)
            minutes = int((uptime_seconds % 3600) // 60)
            seconds = int(uptime_seconds % 60)
            return f"{hours:02}:{minutes:02}:{seconds:02}"
        except Exception as exc:
            raise HWInfoError(f"Failed to read uptime: {exc}")

class HWInfo:
    """
    Provides access to Raspberry Pi system information.

    Args:
        backend (Optional[HWInfoInterface]): Custom backend for testing or non-RPi platforms.

    Raises:
        HWInfoError: If not running on Raspberry Pi and no backend is provided.

    Example:
        >>> hw = HWInfo()
        >>> print(hw.get_cpu_temp())
        >>> print(hw.get_cpu_usage())
        >>> print(hw.get_ram_usage())
        >>> print(hw.get_uptime())

    For testing or on non-RPi platforms, inject a dummy backend:
        >>> class DummyHWInfo:
        ...     def get_cpu_temp(self): return "42.0"
        ...     def get_cpu_usage(self): return "10"
        ...     def get_ram_usage(self): return "20"
        ...     def get_uptime(self): return "00:42:00"
        >>> hw = HWInfo(backend=DummyHWInfo())
        >>> print(hw.get_cpu_temp())
    """
    def __init__(self, backend: Optional[HWInfoInterface] = None) -> None:
        if backend is not None:
            self._backend = backend
        else:
            if not (
                platform.system() == "Linux"
                and ("arm" in platform.machine() or "aarch64" in platform.machine())
            ):
                raise HWInfoError(
                    "Not running on Raspberry Pi hardware. "
                    "Inject a dummy backend for testing."
                )
            self._backend = _RaspberryPiHWInfo()

    def get_cpu_temp(self) -> str:
        """
        Returns the CPU temperature in Celsius as a string (e.g., "48.2").

        Raises:
            HWInfoError: If unable to read the temperature.
        """
        return self._backend.get_cpu_temp()

    def get_cpu_usage(self) -> str:
        """
        Returns the CPU usage percentage as a string (e.g., "12.5").

        Raises:
            HWInfoError: If unable to read CPU usage.
        """
        return self._backend.get_cpu_usage()

    def get_ram_usage(self) -> str:
        """
        Returns the RAM usage percentage as a string (e.g., "42.0").

        Raises:
            HWInfoError: If unable to read RAM usage.
        """
        return self._backend.get_ram_usage()

    def get_uptime(self) -> str:
        """
        Returns the system uptime as a string in HH:MM:SS format.

        Raises:
            HWInfoError: If unable to read uptime.
        """
        return self._backend.get_uptime()