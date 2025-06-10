"""
Asynchronous example: Demonstrate cancelling a Servo movement using DummyPWM.
"""
import asyncio
from examples.dummies import DummyPWM
from aprsrover.servo import Servo

async def main():
    pwm = DummyPWM()
    servo = Servo(channel=3, pwm=pwm)
    print("[Dummy] Async: Starting slow move to 170 degrees (will cancel)...")
    task = asyncio.create_task(servo.set_angle_async(170, speed=5, step=1, step_interval=0.05))
    await asyncio.sleep(0.2)  # Let it move a bit
    print("[Dummy] Async: Cancelling movement...")
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        print("Servo movement cancelled.")
    print(f"Current angle after cancel: {servo.get_angle()}")
    print(f"DummyPWM calls: {pwm.calls}")

if __name__ == "__main__":
    asyncio.run(main())
