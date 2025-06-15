from aprsrover.compass import DummyCompassBackend

class DummyCompass(DummyCompassBackend):
    """
    Dummy compass backend for testing and examples.
    Simulates reading heading.
    """
    def read(self):
        print("DummyCompass.read() called (examples.dummies)")
        return 42.0
