"""
Showcase: Get all hardware info using DummyHWInfo (sync)
"""
import logging
from examples.dummies import DummyHWInfo
from aprsrover.hw_info import HWInfo

logging.basicConfig(level=logging.DEBUG)

def main() -> None:
    hw = HWInfo(backend=DummyHWInfo())
    print(f"CPU Temp: {hw.get_cpu_temp()} °C")
    print(f"CPU Usage: {hw.get_cpu_usage()} %")
    print(f"RAM Usage: {hw.get_ram_usage()} %")
    print(f"Uptime: {hw.get_uptime()}")

if __name__ == "__main__":
    main()
