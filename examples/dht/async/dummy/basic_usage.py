"""
Asynchronous DHT sensor monitoring example (dummy backend).

This example prints temperature and humidity every second for 3 seconds using async monitoring.
Uses: DummyDHT from examples.dummies.dht (no hardware required).
"""
import asyncio
from examples.dummies import DummyDHT
from aprsrover.dht import DHT

def main() -> None:
    dht = DHT(sensor_type='DHT22', pin=4, backend=DummyDHT())

    async def monitor():
        count = 0
        async for temp, humidity in dht.monitor_async(interval=1.0):
            print(f"Dummy async DHT: Temp={temp} C, Humidity={humidity} %")
            count += 1
            if count >= 3:
                break
    asyncio.run(monitor())

if __name__ == "__main__":
    main()
