from aprsrover.hw_info import HWInfoInterface

class DummyHWInfo(HWInfoInterface):
    """
    Dummy hardware info backend for testing and examples.
    Simulates hardware metrics like CPU temperature.
    """
    def get_cpu_temp(self) -> str:
        """Simulate getting CPU temperature in Celsius."""
        return "42.0"

    def get_cpu_usage(self) -> str:
        """Simulate getting CPU usage percentage."""
        return "10"

    def get_ram_usage(self) -> str:
        """Simulate getting RAM usage percentage."""
        return "20"

    def get_uptime(self) -> str:
        """Simulate getting system uptime."""
        return "00:42:00"

    def get_board_name(self) -> str:
        """Simulate getting the board name."""
        return "DummyBoard v1.0"
