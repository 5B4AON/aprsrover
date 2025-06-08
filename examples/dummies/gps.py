from aprsrover.gps import GPSDInterface

class DummyGPS(GPSDInterface):
    """
    Dummy GPS backend for testing and examples.
    Simulates GPS position and movement.
    """
    def get_current(self):
        class Packet:
            lat = 51.5
            lon = -0.1
            time = "2024-01-01T12:00:00.000Z"
            mode = 3
            track = 123.4
        return Packet()

# For examples, you can use: gps = GPS(gpsd=DummyGPS())
