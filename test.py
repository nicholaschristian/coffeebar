import RPi.GPIO as GPIO
import time

# --- Pin mapping with human-friendly names ---
PINS = {
    "LOW_FILL_SENSOR": 18,
    "ESPRESSO_PUMP_RELAY": 23,
}

DELAY = 2  # seconds between state changes

def setup():
    GPIO.setmode(GPIO.BCM)
    for name, pin in PINS.items():
        GPIO.setup(pin, GPIO.OUT)
        GPIO.output(pin, GPIO.LOW)
        print(f"[SETUP] {name} (GPIO {pin}) initialized to LOW")

def cycle_pins():
    try:
        while True:
            for name, pin in PINS.items():
                print(f"[STATE] {name} (GPIO {pin}) is ON")
                GPIO.output(pin, GPIO.HIGH)
                time.sleep(DELAY)

                print(f"[STATE] {name} (GPIO {pin}) is OFF")
                GPIO.output(pin, GPIO.LOW)
                time.sleep(DELAY)
    except KeyboardInterrupt:
        print("\n[INFO] Test stopped by user.")
    finally:
        GPIO.cleanup()
        print("[CLEANUP] GPIO pins reset.")

if __name__ == "__main__":
    print("[INFO] Starting GPIO state tester...")
    setup()
    cycle_pins()
