#!/usr/bin/env python3
import argparse
import time
import RPi.GPIO as GPIO

# -------- Pin configuration (edit here) --------
PINS = {
    # For inputs, we default to pull-up (common for sensors to short to GND)
    "LOW_FILL_SENSOR":     {"pin": 18, "dir": "IN",  "pull": "UP"},
    # For outputs, active_high=True means GPIO.HIGH turns the device ON
    "ESPRESSO_PUMP_RELAY": {"pin": 23, "dir": "OUT", "active_high": True},
}
# ------------------------------------------------

DEFAULT_DELAY = 1.0  # seconds between output toggles

def _setup_gpio():
    GPIO.setmode(GPIO.BCM)
    for name, cfg in PINS.items():
        pin = cfg["pin"]
        if cfg["dir"].upper() == "OUT":
            GPIO.setup(pin, GPIO.OUT, initial=GPIO.LOW)
        else:
            pull = cfg.get("pull", "UP").upper()
            pud = GPIO.PUD_UP if pull == "UP" else GPIO.PUD_DOWN
            GPIO.setup(pin, GPIO.IN, pull_up_down=pud)

def _level_for_on(cfg, on: bool):
    """Translate logical ON/OFF to actual GPIO level considering active_high."""
    if cfg["dir"].upper() != "OUT":
        raise ValueError("Tried to drive an input pin.")
    active_high = bool(cfg.get("active_high", True))
    return GPIO.HIGH if (on == active_high) else GPIO.LOW

def list_pins():
    rows = []
    for name, cfg in PINS.items():
        rows.append(f"- {name}: GPIO {cfg['pin']} [{cfg['dir']}]")
    print("[INFO] Available pins:")
    print("\n".join(rows))

def cycle_all(delay: float):
    """Continuously cycle all OUTPUT pins ON->OFF."""
    outs = [(n, c) for n, c in PINS.items() if c["dir"].upper() == "OUT"]
    if not outs:
        print("[WARN] No OUTPUT pins configured to cycle.")
        return
    print("[INFO] Cycling outputs:", ", ".join(f"{n}(GPIO {c['pin']})" for n, c in outs))
    try:
        while True:
            for name, cfg in outs:
                pin = cfg["pin"]
                print(f"[STATE] {name} (GPIO {pin}) -> ON")
                GPIO.output(pin, _level_for_on(cfg, True))
                time.sleep(delay)
                print(f"[STATE] {name} (GPIO {pin}) -> OFF")
                GPIO.output(pin, _level_for_on(cfg, False))
                time.sleep(delay)
    except KeyboardInterrupt:
        print("\n[INFO] Stopped.")
    finally:
        GPIO.cleanup()
        print("[CLEANUP] GPIO reset.")

def test_pin_output(pin_name: str, cycles: int, delay: float):
    if pin_name not in PINS:
        print(f"[ERROR] Unknown pin '{pin_name}'. Use --list to see options.")
        return
    cfg = PINS[pin_name]
    if cfg["dir"].upper() != "OUT":
        print(f"[ERROR] {pin_name} is configured as INPUT. Use --watch for inputs.")
        return
    pin = cfg["pin"]
    try:
        print(f"[INFO] Testing OUTPUT {pin_name} (GPIO {pin}) for {cycles} cycles...")
        for i in range(1, cycles + 1):
            print(f"[CYCLE {i}] {pin_name} -> ON")
            GPIO.output(pin, _level_for_on(cfg, True))
            time.sleep(delay)
            print(f"[CYCLE {i}] {pin_name} -> OFF")
            GPIO.output(pin, _level_for_on(cfg, False))
            time.sleep(delay)
        print(f"[INFO] Completed testing {pin_name}.")
    except KeyboardInterrupt:
        print("\n[INFO] Interrupted.")
    finally:
        GPIO.cleanup()
        print("[CLEANUP] GPIO reset.")

def test_pin_input(pin_name: str, duration: float, bouncetime_ms: int = 200):
    if pin_name not in PINS:
        print(f"[ERROR] Unknown pin '{pin_name}'. Use --list to see options.")
        return
    cfg = PINS[pin_name]
    if cfg["dir"].upper() != "IN":
        print(f"[ERROR] {pin_name} is configured as OUTPUT. Use --test for outputs.")
        return
    pin = cfg["pin"]

    # Determine "resting high" based on pull; treat transitions to LOW as active for active-low sensors
    pull = cfg.get("pull", "UP").upper()
    resting_high = (pull == "UP")

    def _read_str():
        val = GPIO.input(pin)
        return "HIGH" if val == GPIO.HIGH else "LOW"

    def _callback(_pin):
        val = GPIO.input(pin)
        edge = "RISING" if val == GPIO.HIGH else "FALLING"
        print(f"[EDGE] {pin_name} (GPIO {pin}) {edge} -> { 'HIGH' if val else 'LOW' }")

    print(f"[INFO] Watching INPUT {pin_name} (GPIO {pin}) for {duration:.1f}s "
          f"(pull={'UP' if resting_high else 'DOWN'}, debounce={bouncetime_ms}ms)")
    # Initial state read
    state0 = _read_str()
    print(f"[STATE] Initial: {pin_name} = {state0}")

    try:
        GPIO.add_event_detect(pin, GPIO.BOTH, callback=_callback, bouncetime=bouncetime_ms)
        t_end = time.time() + duration
        # Light polling to show periodic state while we wait for edges
        while time.time() < t_end:
            print(f"[STATE] {pin_name} = {_read_str()}")
            time.sleep(0.5)
        print("[INFO] Done watching input.")
    except KeyboardInterrupt:
        print("\n[INFO] Interrupted.")
    finally:
        GPIO.cleanup()
        print("[CLEANUP] GPIO reset.")

def main():
    parser = argparse.ArgumentParser(description="GPIO dynamic tester (inputs & outputs)")
    sub = parser.add_subparsers(dest="cmd", required=False)

    parser.add_argument("--list", action="store_true", help="List configured pins and exit")

    p_cycle = sub.add_parser("cycle", help="Cycle all OUTPUT pins on/off continuously")
    p_cycle.add_argument("--delay", type=float, default=DEFAULT_DELAY, help="Delay between toggles (s)")

    p_test = sub.add_parser("test", help="Test a single OUTPUT pin by name")
    p_test.add_argument("pin", type=str, help="Pin name (key in PINS)")
    p_test.add_argument("--cycles", type=int, default=3, help="Number of on/off cycles")
    p_test.add_argument("--delay", type=float, default=DEFAULT_DELAY, help="Delay between toggles (s)")

    p_watch = sub.add_parser("watch", help="Watch a single INPUT pin for edges")
    p_watch.add_argument("pin", type=str, help="Pin name (key in PINS)")
    p_watch.add_argument("--duration", type=float, default=20.0, help="Watch time in seconds")
    p_watch.add_argument("--debounce", type=int, default=200, help="Debounce in ms for edge detect")

    args = parser.parse_args()

    if args.__dict__.get("list"):
        list_pins()
        return

    _setup_gpio()

    if args.cmd == "cycle":
        cycle_all(delay=args.delay)
    elif args.cmd == "test":
        test_pin_output(args.pin, cycles=args.cycles, delay=args.delay)
    elif args.cmd == "watch":
        test_pin_input(args.pin, duration=args.duration, bouncetime_ms=args.debounce)
    else:
        # Default behavior: show help + list pins
        list_pins()
        print("\n[HINT] Choose a command, e.g.:")
        print("  sudo python3 gpio_tester.py cycle --delay 0.5")
        print("  sudo python3 gpio_tester.py test ESPRESSO_PUMP_RELAY --cycles 5")
        print("  sudo python3 gpio_tester.py watch LOW_FILL_SENSOR --duration 30")

if __name__ == "__main__":
    main()
`