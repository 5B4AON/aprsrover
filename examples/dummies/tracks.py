from typing import Any
from aprsrover.tracks import PWMControllerInterface

class DummyTracks(PWMControllerInterface):
    """
    Dummy tracks backend for testing and examples.
    Simulates track recording and management.
    """
    def __init__(self):
        self.calls = []
        self.freq = None

    def start_track(self, name: str) -> None:
        """Simulate starting a new track."""
        print(f"[DummyTracks] Started track: {name}")

    def get_tracks(self) -> list[dict[str, Any]]:
        """Simulate retrieving recorded tracks."""
        return [{"name": "TestTrack", "points": 10}]
    
    def set_pwm(self, channel: int, on: int, off: int) -> None:
        self.calls.append((channel, on, off))

    def set_pwm_freq(self, freq: int) -> None:
        self.freq = freq
