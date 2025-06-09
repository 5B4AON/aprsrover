# HW Info Module Documentation

## Overview
The HW Info module provides utilities for querying system information such as CPU temperature, CPU usage, RAM usage, and uptime, supporting both real and dummy backends for testing.

## Features
- Query CPU temperature, CPU usage, RAM usage, and system uptime
- Dependency injection for testability
- Input validation and robust error handling
- Custom exception: `HWInfoError`

## Usage
### Real Hardware Example
```python
from aprsrover.hw_info import HWInfo, HWInfoError
try:
    hw = HWInfo()
    print("CPU Temp:", hw.get_cpu_temp() + "°C")
    print("CPU Usage:", hw.get_cpu_usage() + "%")
    print("RAM Usage:", hw.get_ram_usage() + "%")
    h, m, s = hw.get_uptime().split(":")
    print(f"Uptime: {h}h {m}m {s}s")
except HWInfoError as e:
    print(f"Hardware info error: {e}")
```

### Dummy HW Info Example
```python
from aprsrover.hw_info import HWInfo, HWInfoInterface
class DummyHWInfo(HWInfoInterface):
    def get_cpu_temp(self) -> str: return "42.0"
    def get_cpu_usage(self) -> str: return "10"
    def get_ram_usage(self) -> str: return "20"
    def get_uptime(self) -> str: return "00:42:00"
hw = HWInfo(backend=DummyHWInfo())
print("Dummy CPU Temp:", hw.get_cpu_temp() + "°C")
```

## Notes
- All hardware access is abstracted for easy mocking in tests.
- See the main README and examples for more advanced usage.
