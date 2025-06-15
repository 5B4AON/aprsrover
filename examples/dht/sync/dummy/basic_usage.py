"""
Synchronous DHT sensor usage example (dummy backend).

This example reads temperature and humidity once and prints the result.
Uses: DummyDHT from examples.dummies.dht (no hardware required).
"""
from aprsrover.dht import DHT
from examples.dummies import DummyDHT

def main() -> None:
    dht = DHT(sensor_type='DHT22', pin=4, backend=DummyDHT())
    temp, humidity = dht.read()
    print(f"Dummy sync DHT: Temp={temp} C, Humidity={humidity} %")

if __name__ == "__main__":
    main()
