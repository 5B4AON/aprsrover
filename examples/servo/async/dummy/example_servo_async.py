"""
Asynchronous example: Use DummyPWM and Servo for hardware-free async testing.
"""
import asyncio
from examples.dummies import DummyPWM
from aprsrover.servo import Servo

async def main():
    pwm = DummyPWM()
    servo = Servo(channel=1, pwm=pwm)
    print("[Dummy] Async: Moving instantly to 45 degrees...")
    await servo.set_angle_async(45)
    print(f"Current angle: {servo.get_angle()}")
    await asyncio.sleep(1)

    print("[Dummy] Async: Moving to 135 degrees at 45 deg/sec...")
    await servo.set_angle_async(135, speed=45)
    print(f"Current angle: {servo.get_angle()}")
    await asyncio.sleep(1)

    print("[Dummy] Async: Moving to 90 degrees at 15 deg/sec, 2 deg steps...")
    await servo.set_angle_async(90, speed=15, step=2)
    print(f"Current angle: {servo.get_angle()}")
    await asyncio.sleep(1)

    print(f"DummyPWM calls: {pwm.calls}")

if __name__ == "__main__":
    asyncio.run(main())
