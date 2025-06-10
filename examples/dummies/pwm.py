from aprsrover.tracks import PWMControllerInterface

class DummyPWM(PWMControllerInterface):
    """
    Dummy PWM backend for testing and examples.
    """
    def __init__(self):
        self.calls = []
        self.freq = None
    
    def set_pwm(self, channel: int, on: int, off: int) -> None:
        self.calls.append((channel, on, off))

    def set_pwm_freq(self, freq: int) -> None:
        self.freq = freq
