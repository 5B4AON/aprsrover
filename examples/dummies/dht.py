from aprsrover.dht import DummyDHTBackend

class DummyDHT(DummyDHTBackend):
    """
    Dummy DHT backend for testing and examples.
    Simulates reading temperature and humidity.
    """
    def read(self):
        print("DummyDHT.read() called (examples.dummies)")
        return (23.0, 50.0)
