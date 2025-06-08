from aprsrover.aprs import KISSInterface
from ax253 import Frame
from typing import Any

class DummyKissProtocol:
    def __init__(self):
        self.written_frames: list[Frame] = []
        self.read_frames: list[Frame] = []
        self.read_called = False

    def write(self, frame: Frame) -> None:
        self.written_frames.append(frame)

    async def read(self):
        self.read_called = True
        for frame in self.read_frames:
            yield frame

class DummyAPRS(KISSInterface):
    """
    Dummy APRS backend for testing and examples.
    Simulates sending and receiving APRS messages.
    """
    def __init__(self):
        self.protocol = DummyKissProtocol()
        self.create_called = False

    async def create_tcp_connection(self, host: str, port: int, kiss_settings: dict) -> tuple[Any, Any]:
        self.create_called = True
        return (object(), self.protocol)

    def write(self, frame: Frame) -> None:
        self.protocol.write(frame)

    def read(self):
        return self.protocol.read()
