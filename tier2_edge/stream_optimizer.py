import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import BATCH_SIZE, PRIORITY

class StreamOptimizer:
    def __init__(self):
        self.batch = []
        self.batch_number = 0

    def is_critical(self, record):
        if record.get("has_critical_alert", False):
            return True
        hr = record.get("HeartRate")
        spo2 = record.get("SpO2")
        if hr and isinstance(hr, (int, float)) and hr > 150:
            return True
        if spo2 and isinstance(spo2, (int, float)) and spo2 < 90:
            return True
        return False

    def add(self, record):
        if self.is_critical(record):
            return {
                "type": "CRITICAL_BYPASS",
                "reason": "Critical alert — skipped batching",
                "record": record,
                "batch_number": None,
                "optimized": True
            }
        self.batch.append(record)
        if len(self.batch) >= BATCH_SIZE:
            return self.flush()
        return None

    def flush(self):
        if not self.batch:
            return None
        self.batch_number += 1
        aggregated = self._aggregate(self.batch)
        result = {
            "type": "BATCH",
            "batch_number": self.batch_number,
            "batch_size": len(self.batch),
            "aggregated": aggregated,
            "timestamps": [r.get("timestamp") for r in self.batch],
            "vendors": list(set(r.get("original_vendor", "?") for r in self.batch)),
            "optimized": True
        }
        self.batch = []
        return result

    def _aggregate(self, records):
        vitals = ["HeartRate", "SpO2", "Glucose", "Temperature"]
        aggregated = {}
        for vital in vitals:
            values = [
                r[vital] for r in records
                if vital in r and isinstance(r[vital], (int, float))
            ]
            if values:
                aggregated[vital] = {
                    "avg": round(sum(values) / len(values), 2),
                    "min": min(values),
                    "max": max(values),
                    "count": len(values)
                }
        return aggregated


if __name__ == "__main__":
    from tier1_device.sensor_simulator import generate_reading
    from tier1_device.preprocessing import preprocess
    from tier1_device.threshold_detector import check_thresholds
    from tier2_edge.interoperability_engine import adapt

    print("\n" + "="*55)
    print("  Stream Optimizer — TEST")
    print("="*55)

    optimizer = StreamOptimizer()
    print(f"\nSending {BATCH_SIZE} routine readings...")

    for i in range(BATCH_SIZE):
        raw = generate_reading()
        cleaned = preprocess(raw)
        checked = check_thresholds(cleaned)
        standard = adapt(checked)
        result = optimizer.add(standard)

        if result is None:
            print(f"  Reading {i+1}: buffering... ({len(optimizer.batch)}/{BATCH_SIZE})")
        elif result["type"] == "CRITICAL_BYPASS":
            print(f"  Reading {i+1}: CRITICAL BYPASS sent immediately")
        else:
            print(f"\n  Reading {i+1}: BATCH FLUSHED")
            print(f"  Batch size   : {result['batch_size']}")
            print(f"  Vendors seen : {result['vendors']}")
            for vital, stats in result["aggregated"].items():
                print(f"    {vital}: avg={stats['avg']}  min={stats['min']}  max={stats['max']}")

    print("\n" + "="*55)
    print("  TESTING CRITICAL BYPASS")
    print("="*55)

    critical_raw = generate_reading("Philips")
    critical_raw["HR"] = 185
    critical_raw["spo2"] = 82
    cleaned = preprocess(critical_raw)
    checked = check_thresholds(cleaned)
    standard = adapt(checked)
    result = optimizer.add(standard)

    print(f"  Type   : {result['type']}")
    print(f"  Reason : {result['reason']}")
    print(f"  Bypassed batching: yes")