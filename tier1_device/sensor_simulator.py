# sensor_simulator.py
# Simulates three different vendors sending physiological data
# Each vendor uses different field names — this is the problem
# that the Interoperability Engine will solve

import random
import time
from datetime import datetime
import sys
import os

# Import config from parent folder
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import VENDORS, THRESHOLDS

def generate_philips_reading():
    """Philips uses: HR, temp (Fahrenheit), spo2, gluc"""
    return {
        "vendor": "Philips",
        "HR": random.randint(55, 170),
        "spo2": round(random.uniform(88, 100), 1),
        "gluc": random.randint(60, 200),
        "temp": round(random.uniform(97.0, 101.0), 1),  # Fahrenheit
        "ecg": [round(random.uniform(-1, 1), 3) for _ in range(10)],
        "timestamp": datetime.now().isoformat()
    }

def generate_ge_reading():
    """GE uses: heartRate, temperature (Celsius), oxygen, bloodSugar"""
    return {
        "vendor": "GE",
        "heartRate": random.randint(55, 170),
        "oxygen": round(random.uniform(88, 100), 1),
        "bloodSugar": random.randint(60, 200),
        "temperature": round(random.uniform(36.1, 38.3), 1),  # Celsius
        "ecg": [round(random.uniform(-1, 1), 3) for _ in range(10)],
        "timestamp": datetime.now().isoformat()
    }

def generate_siemens_reading():
    """Siemens uses: pulse, temp_c, o2_sat, glucose_level"""
    return {
        "vendor": "Siemens",
        "pulse": random.randint(55, 170),
        "o2_sat": round(random.uniform(88, 100), 1),
        "glucose_level": random.randint(60, 200),
        "temp_c": round(random.uniform(36.1, 38.3), 1),  # Celsius
        "ecg": [round(random.uniform(-1, 1), 3) for _ in range(10)],
        "timestamp": datetime.now().isoformat()
    }

def generate_reading(vendor=None):
    """Generate one reading from a random or specified vendor"""
    if vendor is None:
        vendor = random.choice(VENDORS)

    if vendor == "Philips":
        return generate_philips_reading()
    elif vendor == "GE":
        return generate_ge_reading()
    elif vendor == "Siemens":
        return generate_siemens_reading()

def simulate_stream(interval_seconds=1, count=None):
    """
    Continuously generate readings from random vendors.
    interval_seconds: how often to generate a reading
    count: how many readings (None = infinite)
    """
    generated = 0
    print("\n" + "="*50)
    print("  SaMD Sensor Simulator — STARTED")
    print("="*50)

    while True:
        reading = generate_reading()
        vendor = reading["vendor"]

        print(f"\n[{reading['timestamp']}]")
        print(f"Vendor : {vendor}")
        print(f"Data   : {reading}")

        generated += 1
        if count and generated >= count:
            break

        time.sleep(interval_seconds)

# ── Run directly to test ───────────────────────────
if __name__ == "__main__":
    simulate_stream(interval_seconds=2, count=5)