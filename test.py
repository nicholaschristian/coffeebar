import RPi.GPIO as GPIO
import time

# List of GPIO pins you want to test
TEST_PINS = [18,23]  # Adjust for your Pi model

# Delay between state changes
DELAY = 1  # seconds

def setup():
    GPIO.setmode(GPIO.BCM)
    for pin in TEST_PINS:
        GPIO.setup(pin, GPIO.OUT)
        GPIO.output(pin, GPIO.LOW)

def cycle_pins():
    try:
        while True:
            for pin in TEST_PINS:
                print(f"[INFO] Setting GPIO {pin} HIGH")
                GPIO.output(pin, GPIO.HIGH)
                time.sleep(DELAY)
                print(f"[INFO] Setting GPIO {pin} LOW")
                GPIO.output(pin, GPIO.LOW)
                time.sleep(DELAY)
    except KeyboardInterrupt:
        print("\n[INFO] Stopping test...")
    finally:
        GPIO.cleanup()
        print("[INFO] GPIO cleanup done.")

if __name__ == "__main__":
    print(f"[INFO] Testing GPIO pins: {TEST_PINS}")
    setup()
    cycle_pins()
