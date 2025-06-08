import unittest
from aprsrover.hw_info import HWInfo, HWInfoError, HWInfoInterface

class DummyHWInfo(HWInfoInterface):
    def get_cpu_temp(self) -> str:
        return "42.0"
    def get_cpu_usage(self) -> str:
        return "10"
    def get_ram_usage(self) -> str:
        return "20"
    def get_uptime(self) -> str:
        return "00:42:00"

class FailingHWInfo(HWInfoInterface):
    def get_cpu_temp(self) -> str:
        raise HWInfoError("fail temp")
    def get_cpu_usage(self) -> str:
        raise HWInfoError("fail cpu")
    def get_ram_usage(self) -> str:
        raise HWInfoError("fail ram")
    def get_uptime(self) -> str:
        raise HWInfoError("fail uptime")

class TestHWInfo(unittest.TestCase):
    def setUp(self):
        self.hw = HWInfo(backend=DummyHWInfo())

    def test_get_cpu_temp(self):
        self.assertEqual(self.hw.get_cpu_temp(), "42.0")

    def test_get_cpu_usage(self):
        self.assertEqual(self.hw.get_cpu_usage(), "10")

    def test_get_ram_usage(self):
        self.assertEqual(self.hw.get_ram_usage(), "20")

    def test_get_uptime(self):
        self.assertEqual(self.hw.get_uptime(), "00:42:00")

    def test_failures_raise_hwinfoerror(self):
        hw = HWInfo(backend=FailingHWInfo())
        with self.assertRaises(HWInfoError):
            hw.get_cpu_temp()
        with self.assertRaises(HWInfoError):
            hw.get_cpu_usage()
        with self.assertRaises(HWInfoError):
            hw.get_ram_usage()
        with self.assertRaises(HWInfoError):
            hw.get_uptime()

    def test_no_backend_non_rpi(self):
        import platform
        # Simulate non-RPi platform
        orig_system = platform.system
        orig_machine = platform.machine
        platform.system = lambda: "Darwin"
        platform.machine = lambda: "x86_64"
        try:
            with self.assertRaises(HWInfoError):
                HWInfo()
        finally:
            platform.system = orig_system
            platform.machine = orig_machine

if __name__ == "__main__":
    unittest.main()