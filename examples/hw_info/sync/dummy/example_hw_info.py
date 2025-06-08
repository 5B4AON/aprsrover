"""
Example: Get hardware info using the Dummy backend (synchronous).
"""
from examples.dummies import DummyHWInfo
from aprsrover.hw_info import HWInfo
import logging

logging.basicConfig(level=logging.DEBUG)

def main() -> None:
    hw = HWInfo(backend=DummyHWInfo())
    print("Dummy CPU Temp:", hw.get_cpu_temp() + "°C")
    print("Dummy CPU Usage:", hw.get_cpu_usage() + "%")
    print("Dummy RAM Usage:", hw.get_ram_usage() + "%")
    h, m, s = hw.get_uptime().split(":")
    print(f"Dummy Uptime: {h}h {m}m {s}s")

if __name__ == "__main__":
    main()
