from aprsrover.gps import GPSDInterface

class DummyGPS(GPSDInterface):
    """
    Dummy GPS backend for testing and examples.
    Simulates GPS position and movement.
    """
    def get_current(self):
        class Packet:
            lat = 35.15954748
            lon = 33.30987698
            time = "2025-01-01T12:00:00.000Z"
            mode = 3
            track = 180
        return Packet()

# For examples, you can use: gps = GPS(gpsd=DummyGPS())
