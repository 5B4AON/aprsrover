"""
Synchronous example: Use DummyPWM and Servo for hardware-free testing.
"""
from examples.dummies import DummyPWM
from aprsrover.servo import Servo
import time

def main():
    pwm = DummyPWM()
    servo = Servo(channel=0, pwm=pwm)
    print("[Dummy] Moving instantly to 90 degrees...")
    servo.set_angle(90)
    print(f"Current angle: {servo.get_angle()}")
    time.sleep(1)

    print("[Dummy] Moving to 0 degrees at 60 deg/sec...")
    servo.set_angle(0, speed=60)
    print(f"Current angle: {servo.get_angle()}")
    time.sleep(1)

    print("[Dummy] Moving to 180 degrees at 30 deg/sec, with 5 deg steps...")
    servo.set_angle(180, speed=30, step=5)
    print(f"Current angle: {servo.get_angle()}")
    time.sleep(1)

    print("[Dummy] Testing input validation (should clamp to min/max)...")
    servo.set_angle(-100)
    print(f"Clamped angle: {servo.get_angle()}")
    servo.set_angle(999)
    print(f"Clamped angle: {servo.get_angle()}")
    print(f"DummyPWM calls: {pwm.calls}")

if __name__ == "__main__":
    main()
