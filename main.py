import logging
import RPi.GPIO as GPIO

# --- Logging Configuration ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)


class Device:
    def __init__(self, name: str, pin_number: int, io_type: str):
        self.pin_number = pin_number
        self.name = name
        if io_type.upper() not in ["IN", "OUT"]:
            raise ValueError("Invalid io_type. IO types must be `IN` or `OUT`")
        self.io_type = io_type.upper()

    def set_state(self, state: bool):
        if self.io_type == "IN":
            raise TypeError(f"Cannot set state `{state}` on input device `{self.name}`.")
        logger.info(f"Setting {self.name} (pin {self.pin_number}) to {'ON' if state else 'OFF'}")
        GPIO.output(self.pin_number, state)


class Sensor(Device):
    @property
    def get_state(self):
        if self.io_type == "OUT":
            raise TypeError(f"Cannot read state of output device `{self.name}`.")
        state = GPIO.input(self.pin_number)
        logger.debug(f"Reading {self.name} (pin {self.pin_number}): {'HIGH' if state else 'LOW'}")
        return state

    @property
    def water_detected(self):
        return self.get_state


class CoffeeBar:
    def __init__(self):
        self.HIGH_FILL_SENSOR = Sensor("HIGH_FILL_SENSOR", 1, "IN")
        self.TEMPERATURE_SENSOR = Sensor("TEMPERATURE_SENSOR", 2, "IN")
        self.ESPRESSO_PUMP = Device("ESPRESSO_PUMP", 3, "OUT")  # Pin updated to avoid conflict
        self.FILTER_PUMP = Device("FILTER_PUMP", 4, "OUT")
        self.PULSE_PUMP_BTN = Device("PULSE_PUMP_BTN", 5, "IN")




        self.LOW_FILL_SENSOR = Sensor("LOW_FILL_SENSOR", 18, "IN")
        self.ESPRESSO_PUMP_RELAY = Device("ESPRESSO_PUMP_RELAY", 23, "OUT")

        self.__SETUP__()

    def __SETUP__(self):
        devices = [
            self.LOW_FILL_SENSOR,
            self.HIGH_FILL_SENSOR,
            self.TEMPERATURE_SENSOR,
            self.ESPRESSO_PUMP,
            self.FILTER_PUMP
        ]
        GPIO.setmode(GPIO.BCM)
        for device in devices:
            GPIO.setup(device.pin_number, GPIO.IN if device.io_type == "IN" else GPIO.OUT)
            logger.info(f"Configured {device.name} on pin {device.pin_number} as {device.io_type}")


if __name__ == '__main__':
    cb = CoffeeBar()
    logger.info("CoffeeBar system initialized. Starting loop...")
    try:
        while True:
            if cb.LOW_FILL_SENSOR.water_detected:
                logger.info("Low fill detected: turning ON espresso pump.")
                cb.ESPRESSO_PUMP.set_state(True)
            if cb.HIGH_FILL_SENSOR.water_detected:
                logger.info("High fill detected: turning OFF espresso pump.")
                cb.ESPRESSO_PUMP.set_state(False)
    except KeyboardInterrupt:
        logger.info("Shutting down CoffeeBar system.")
        GPIO.cleanup()
