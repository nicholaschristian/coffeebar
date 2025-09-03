#!/usr/bin/env python3
import argparse
import time
import sys
from typing import Dict, Any
import RPi.GPIO as GPIO

# ---------------- Pin configuration ----------------
PINS: Dict[str, Dict[str, Any]] = {
    "LOW_FILL_SENSOR":     {"pin": 18, "dir": "IN",  "pull": "UP",  "active_low": True},
    "ESPRESSO_PUMP_RELAY": {"pin": 23, "dir": "OUT", "active_high": True},
}
# ---------------------------------------------------

DEFAULT_DELAY = 1.0
DEFAULT_DEBOUNCE_MS = 200

def _setup_gpio():
    GPIO.setmode(GPIO.BCM)
    for name, cfg in PINS.items():
        pin = cfg["pin"]
        if cfg["dir"].upper() == "OUT":
            GPIO.setup(pin, GPIO.OUT, initial=GPIO.LOW)
        else:
            pull = cfg.get("pull", "UP").upper()
            if pull == "UP":
                pud = GPIO.PUD_UP
            elif pull == "DOWN":
                pud = GPIO.PUD_DOWN
            else:
                pud = GPIO.PUD_OFF
            GPIO.setup(pin, GPIO.IN, pull_up_down=pud)

def _level_for_on(cfg, on: bool):
    if cfg["dir"].upper() != "OUT":
        raise ValueError("Tried to drive an input pin.")
    active_high = bool(cfg.get("active_high", True))
    return GPIO.HIGH if (on == active_high) else GPIO.LOW

def list_pins():
    print("[INFO] Available pins:")
    for name, cfg in PINS.items():
        row = f"- {name}: GPIO {cfg['pin']} [{cfg['dir']}"
        if cfg["dir"].upper() == "IN":
            row += f", pull={cfg.get('pull','UP')}"
            if cfg.get("active_low"):
                row += ", active-low"
        else:
            row += f", active_high={cfg.get('active_high', True)}"
        row += "]"
        print(row)

def cycle_all(delay: float):
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
        print(f"[ERROR] {pin_name} is INPUT. Use 'watch' for inputs.")
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

def set_output(pin_name: str, state: str):
    if pin_name not in PINS:
        print(f"[ERROR] Unknown pin '{pin_name}'. Use --list to see options.")
        return
    cfg = PINS[pin_name]
    if cfg["dir"].upper() != "OUT":
        print(f"[ERROR] {pin_name} is INPUT. Cannot set an input.")
        return
    pin = cfg["pin"]
    state_norm = state.strip().lower()
    logical_on = state_norm in ("on", "high", "1", "true")
    try:
        GPIO.output(pin, _level_for_on(cfg, logical_on))
        phys = "HIGH" if GPIO.input(pin) == GPIO.HIGH else "LOW"
        print(f"[INFO] {pin_name} (GPIO {pin}) set to {'ON' if logical_on else 'OFF'} (physical {phys})")
    finally:
        GPIO.cleanup()
        print("[CLEANUP] GPIO reset.")

def _fmt_input(name: str, level: int):
    active_low = bool(PINS[name].get("active_low", False))
    logical = "ACTIVE" if (level == GPIO.LOW and active_low) or (level == GPIO.HIGH and not active_low) else "INACTIVE"
    return f"{name} = {'LOW' if level == GPIO.LOW else 'HIGH'} ({logical})"

def watch_input(pin_name: str, duration: float, bouncetime_ms: int):
    if pin_name not in PINS:
        print(f"[ERROR] Unknown pin '{pin_name}'. Use --list to see options.")
        return
    cfg = PINS[pin_name]
    if cfg["dir"].upper() != "IN":
        print(f"[ERROR] {pin_name} is OUTPUT. Use 'test' or 'set' for outputs.")
        return
    pin = cfg["pin"]

    def _callback(_pin):
        val = GPIO.input(pin)
        edge = "RISING" if val == GPIO.HIGH else "FALLING"
        print(f"[EDGE] {pin_name} (GPIO {pin}) {edge} -> {_fmt_input(pin_name, val)}")

    print(f"[INFO] Watching INPUT {pin_name} (GPIO {pin}) for {duration:.1f}s (debounce={bouncetime_ms}ms)")
    try:
        s0 = GPIO.input(pin)
        print(f"[STATE] Initial: {_fmt_input(pin_name, s0)}")
        GPIO.add_event_detect(pin, GPIO.BOTH, callback=_callback, bouncetime=bouncetime_ms)
        t_end = time.time() + duration
        while time.time() < t_end:
            now = GPIO.input(pin)
            print(f"[STATE] {_fmt_input(pin_name, now)}")
            time.sleep(0.5)
        print("[INFO] Done watching input.")
    except KeyboardInterrupt:
        print("\n[INFO] Interrupted.")
    finally:
        GPIO.cleanup()
        print("[CLEANUP] GPIO reset.")

def main():
    parser = argparse.ArgumentParser(description="GPIO dynamic tester (inputs & outputs)")
    parser.add_argument("--list", action="store_true", help="List configured pins and exit")
    sub = parser.add_subparsers(dest="cmd", required=False)

    p_cycle = sub.add_parser("cycle", help="Cycle all OUTPUT pins on/off continuously")
    p_cycle.add_argument("--delay", type=float, default=DEFAULT_DELAY, help="Delay between toggles (s)")

    p_test = sub.add_parser("test", help="Test a single OUTPUT pin by name")
    p_test.add_argument("pin", type=str, help="Pin name (key in PINS)")
    p_test.add_argument("--cycles", type=int, default=3, help="Number of on/off cycles")
    p_test.add_argument("--delay", type=float, default=DEFAULT_DELAY, help="Delay between toggles (s)")

    p_watch = sub.add_parser("watch", help="Watch a single INPUT pin for edges")
    p_watch.add_argument("pin", type=str, help="Pin name (key in PINS)")
    p_watch.add_argument("--duration", type=float, default=20.0, help="Watch time in seconds")
    p_watch.add_argument("--debounce", type=int, default=DEFAULT_DEBOUNCE_MS, help="Debounce in ms")

    p_set = sub.add_parser("set", help="Manually set an OUTPUT pin to on/off")
    p_set.add_argument("pin", type=str, help="Pin name (key in PINS)")
    p_set.add_argument("state", type=str, help="on|off|high|low|1|0|true|false")

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
        watch_input(args.pin, duration=args.duration, bouncetime_ms=args.debounce)
    elif args.cmd == "set":
        set_output(args.pin, args.state)
    else:
        list_pins()
        print("\n[HINT] Examples:")
        print("  sudo python3 gpio_tester.py cycle --delay 0.5")
        print("  sudo python3 gpio_tester.py test ESPRESSO_PUMP_RELAY --cycles 5")
        print("  sudo python3 gpio_tester.py watch LOW_FILL_SENSOR --duration 30")
        print("  sudo python3 gpio_tester.py set ESPRESSO_PUMP_RELAY on")

if __name__ == "__main__":
    try:
        main()
    except Exception:
        GPIO.cleanup()
        print("[CLEANUP] GPIO reset due to exception.", file=sys.stderr)
        raise
