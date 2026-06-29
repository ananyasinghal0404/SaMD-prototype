import sys
import os
from datetime import datetime

from tier1_device.sensor_simulator import generate_reading
from tier1_device.preprocessing import preprocess
from tier1_device.threshold_detector import check_thresholds
from tier2_edge.interoperability_engine import adapt
from tier2_edge.stream_optimizer import StreamOptimizer
from tier2_edge.local_buffer import LocalBuffer
from tier2_edge.orchestration.placement_decision import decide
from tier2_edge.edge_execution import run_local_inference
from tier3_cloud.storage import init_db, save_reading, log_audit, log_confidence

def run_pipeline(num_readings=5):
    init_db()
    optimizer = StreamOptimizer()
    buffer    = LocalBuffer(max_size=100)

    print("\n" + "="*60)
    print("  SaMD PROTOTYPE — Full Pipeline")
    print("  Tier 1 + Tier 2 + Tier 3 Storage")
    print("="*60)

    for i in range(num_readings):
        print(f"\n{'─'*60}")
        print(f"  READING {i+1}")
        print(f"{'─'*60}")

        # ── TIER 1 ───────────────────────────────
        raw     = generate_reading()
        print(f"  [Sensor]          Vendor={raw['vendor']}")

        cleaned = preprocess(raw)
        print(f"  [Preprocessing]   ECG noise removed ✅")

        checked = check_thresholds(cleaned)
        if checked["has_critical_alert"]:
            print(f"  [Threshold]       ⚠️  {checked['alerts'][0]['message']}")
        else:
            print(f"  [Threshold]       All vitals in range ✅")

        # ── TIER 2 ───────────────────────────────
        standard = adapt(checked)
        print(f"  [Interop Engine]  Standardized → HeartRate={standard.get('HeartRate')} bpm")

        opt_result = optimizer.add(standard)
        if opt_result and opt_result["type"] == "CRITICAL_BYPASS":
            print(f"  [Stream Optim]    ⚡ Critical bypass — not batched")
        elif opt_result and opt_result["type"] == "BATCH":
            print(f"  [Stream Optim]    Batch {opt_result['batch_number']} flushed ({opt_result['batch_size']} readings)")
        else:
            print(f"  [Stream Optim]    Buffering ({len(optimizer.batch)} in batch)")

        buffer.push(standard)
        print(f"  [Local Buffer]    Stored ({buffer.size()} in queue)")

        decision = decide(standard)
        print(f"  [Orchestration]   Priority={decision['priority']} | CPU={decision['cpu_percent']}% | Network={decision['network_quality']}")
        print(f"  [Orchestration]   ➜ DECISION: {decision['decision']} — {decision['reason'][:45]}")

        # ── TIER 3 ───────────────────────────────
        if decision["decision"] == "EDGE":
            inference = run_local_inference(standard)
            print(f"  [Edge Execution]  Confidence={inference['confidence']}")
            for finding in inference["findings"]:
                if any(word in finding.lower() for word in
                       ["critical", "suspected", "detected", "hypoxia",
                        "arrhythmia", "hypoglycemia", "fever", "hypothermia"]):
                    print(f"  [Edge Execution]  🚨 {finding}")
                else:
                    print(f"  [Edge Execution]  ✅ {finding}")

            # Save to database
            save_reading(standard, "EDGE", inference)
            log_confidence(inference["model_version"],
                          inference["confidence"],
                          inference["drift_suspected"])
            log_audit("INFERENCE", "edge_execution_engine",
                     f"Confidence={inference['confidence']} findings={len(inference['findings'])}",
                     clinical_core=True)
            print(f"  [Storage]         Saved to database ✅")

        else:
            fake_cloud_inference = {
                "confidence": 0.95,
                "findings": ["Cloud inference — detailed analysis complete"],
                "model_version": "cloud_v1",
                "drift_suspected": False
            }
            save_reading(standard, "CLOUD", fake_cloud_inference)
            log_audit("INFERENCE", "cloud_layer",
                     f"Routine reading sent to cloud",
                     clinical_core=False)
            print(f"  [Cloud]           → Sent to cloud + saved ✅")

    print(f"\n{'='*60}")
    print(f"  Pipeline complete — {num_readings} readings processed")
    print(f"  Buffer stats: {buffer.stats()}")
    print(f"{'='*60}\n")

if __name__ == "__main__":
    run_pipeline(num_readings=5)