# interoperability_engine.py
# Gap 3 — Interoperability and Semantic Data Silos
# 
# THREE RESPONSIBILITIES:
# 1. Device Adaptation   — convert vendor-specific formats to common format
# 2. Semantic Mapping    — HR / heartRate / pulse → HeartRate
# 3. Unit Normalization  — 98.6°F → 37°C
#
# Input:  raw vendor reading (any of Philips, GE, Siemens)
# Output: one standardized record regardless of vendor

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ── Semantic mapping tables ───────────────────────
# These map every vendor field name to our standard name
FIELD_MAP = {
    # Heart rate
    "HR":          "HeartRate",
    "heartRate":   "HeartRate",
    "pulse":       "HeartRate",

    # SpO2
    "spo2":        "SpO2",
    "oxygen":      "SpO2",
    "o2_sat":      "SpO2",

    # Glucose
    "gluc":        "Glucose",
    "bloodSugar":  "Glucose",
    "glucose_level": "Glucose",

    # Temperature
    "temp":        "Temperature",
    "temperature": "Temperature",
    "temp_c":      "Temperature",

    # ECG — same name across vendors
    "ecg":         "ECG",
}

# Fields to DROP from output — vendor metadata not needed downstream
DROP_FIELDS = ["vendor", "preprocessed", "threshold_checked",
               "values_checked", "alerts", "alert_count",
               "has_critical_alert"]

def fahrenheit_to_celsius(f):
    """Convert Fahrenheit to Celsius, rounded to 1 decimal"""
    return round((f - 32) * 5 / 9, 1)

def normalize_units(standard_record, original_vendor):
    """
    Unit normalization step.
    Philips sends temperature in Fahrenheit — convert to Celsius.
    All others already send Celsius.
    """
    if original_vendor == "Philips":
        if "Temperature" in standard_record:
            fahrenheit = standard_record["Temperature"]
            standard_record["Temperature"] = fahrenheit_to_celsius(fahrenheit)
            standard_record["Temperature_unit"] = "Celsius"
            standard_record["Temperature_converted_from"] = f"{fahrenheit}°F"
    else:
        if "Temperature" in standard_record:
            standard_record["Temperature_unit"] = "Celsius"

    if "HeartRate" in standard_record:
        standard_record["HeartRate_unit"] = "bpm"

    if "SpO2" in standard_record:
        standard_record["SpO2_unit"] = "%"

    if "Glucose" in standard_record:
        standard_record["Glucose_unit"] = "mg/dL"

    return standard_record

def adapt(reading):
    """
    Main function — takes any vendor reading,
    returns a fully standardized record.

    Step 1: Device Adaptation — map vendor fields to standard fields
    Step 2: Semantic Mapping  — already done via FIELD_MAP
    Step 3: Unit Normalization — convert units to standard
    """
    original_vendor = reading.get("vendor", "Unknown")
    standard_record = {}

    # ── Step 1 + 2: Device adaptation + semantic mapping ──
    for key, value in reading.items():
        if key in DROP_FIELDS:
            continue
        if key in FIELD_MAP:
            standard_name = FIELD_MAP[key]
            standard_record[standard_name] = value
        else:
            # Keep fields we don't explicitly map (like timestamp)
            standard_record[key] = value

    # ── Step 3: Unit normalization ────────────────
    standard_record = normalize_units(standard_record, original_vendor)

    # ── Add metadata ──────────────────────────────
    standard_record["original_vendor"] = original_vendor
    standard_record["interoperability_processed"] = True

    return standard_record


# ── Run directly to test ──────────────────────────
if __name__ == "__main__":
    import json
    from tier1_device.sensor_simulator import generate_reading
    from tier1_device.preprocessing import preprocess
    from tier1_device.threshold_detector import check_thresholds

    print("\n" + "="*55)
    print("  Interoperability Engine — TEST")
    print("="*55)

    for vendor in ["Philips", "GE", "Siemens"]:
        raw     = generate_reading(vendor)
        cleaned = preprocess(raw)
        checked = check_thresholds(cleaned)
        standard = adapt(checked)

        print(f"\nVendor  : {vendor}")
        print(f"BEFORE  : ", end="")

        # Show only the vital fields before
        if vendor == "Philips":
            print({
                "HR": raw["HR"],
                "temp": f"{raw['temp']}°F",
                "spo2": raw["spo2"],
                "gluc": raw["gluc"]
            })
        elif vendor == "GE":
            print({
                "heartRate": raw["heartRate"],
                "temperature": f"{raw['temperature']}°C",
                "oxygen": raw["oxygen"],
                "bloodSugar": raw["bloodSugar"]
            })
        elif vendor == "Siemens":
            print({
                "pulse": raw["pulse"],
                "temp_c": f"{raw['temp_c']}°C",
                "o2_sat": raw["o2_sat"],
                "glucose_level": raw["glucose_level"]
            })

        print(f"AFTER   : ", end="")
        print({
            "HeartRate": f"{standard.get('HeartRate')} {standard.get('HeartRate_unit','')}",
            "Temperature": f"{standard.get('Temperature')}°C",
            "SpO2": f"{standard.get('SpO2')} {standard.get('SpO2_unit','')}",
            "Glucose": f"{standard.get('Glucose')} {standard.get('Glucose_unit','')}",
        })

        if "Temperature_converted_from" in standard:
            print(f"Converted: {standard['Temperature_converted_from']} → {standard['Temperature']}°C")

        print(f"Standard: {standard['interoperability_processed']}")

    print("\n" + "="*55)
    print("  All 3 vendors → ONE standard format ✅")
    print("="*55)