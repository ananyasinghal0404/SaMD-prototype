import sys
import os
import sqlite3
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import DB_PATH

def get_connection():
    return sqlite3.connect(DB_PATH)

def get_summary_stats():
    """
    Computes overall statistics across all readings.
    Population-level analytics.
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM readings")
    total = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM readings WHERE decision='EDGE'")
    edge_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM readings WHERE decision='CLOUD'")
    cloud_count = cursor.fetchone()[0]

    cursor.execute("SELECT AVG(heart_rate), MIN(heart_rate), MAX(heart_rate) FROM readings WHERE heart_rate IS NOT NULL")
    hr_stats = cursor.fetchone()

    cursor.execute("SELECT AVG(spo2), MIN(spo2), MAX(spo2) FROM readings WHERE spo2 IS NOT NULL")
    spo2_stats = cursor.fetchone()

    cursor.execute("SELECT AVG(glucose), MIN(glucose), MAX(glucose) FROM readings WHERE glucose IS NOT NULL")
    glucose_stats = cursor.fetchone()

    cursor.execute("SELECT AVG(confidence) FROM readings WHERE confidence IS NOT NULL")
    avg_confidence = cursor.fetchone()[0]

    conn.close()

    return {
        "total_readings": total,
        "edge_decisions": edge_count,
        "cloud_decisions": cloud_count,
        "edge_percent": round(edge_count / total * 100, 1) if total > 0 else 0,
        "heart_rate": {
            "avg": round(hr_stats[0], 1) if hr_stats[0] else None,
            "min": hr_stats[1],
            "max": hr_stats[2]
        },
        "spo2": {
            "avg": round(spo2_stats[0], 1) if spo2_stats[0] else None,
            "min": spo2_stats[1],
            "max": spo2_stats[2]
        },
        "glucose": {
            "avg": round(glucose_stats[0], 1) if glucose_stats[0] else None,
            "min": glucose_stats[1],
            "max": glucose_stats[2]
        },
        "avg_confidence": round(avg_confidence, 3) if avg_confidence else None
    }

def get_critical_events():
    """Returns all readings that were routed to edge (critical)"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT timestamp, vendor, heart_rate, spo2, glucose, findings
        FROM readings
        WHERE decision='EDGE'
        ORDER BY id DESC
        LIMIT 10
    """)
    rows = cursor.fetchall()
    conn.close()
    return rows

def get_drift_trend():
    """
    Analyzes confidence scores over time.
    Returns trend for drift detection monitor.
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT timestamp, confidence, drift_suspected
        FROM confidence_log
        ORDER BY id ASC
    """)
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        return {"trend": "NO_DATA", "logs": []}

    confidences = [r[1] for r in rows]
    avg = round(sum(confidences) / len(confidences), 3)
    drift_count = sum(1 for r in rows if r[2] == 1)

    if len(confidences) >= 2:
        recent_avg = round(sum(confidences[-3:]) / len(confidences[-3:]), 3)
        early_avg  = round(sum(confidences[:3]) / len(confidences[:3]), 3)
        trend = "DEGRADING" if recent_avg < early_avg - 0.05 else "STABLE"
    else:
        trend = "INSUFFICIENT_DATA"
        recent_avg = avg
        early_avg  = avg

    return {
        "total_logs": len(rows),
        "avg_confidence": avg,
        "early_avg": early_avg,
        "recent_avg": recent_avg,
        "drift_count": drift_count,
        "trend": trend,
        "logs": rows
    }

def get_vendor_breakdown():
    """How many readings came from each vendor"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT vendor, COUNT(*) as count
        FROM readings
        GROUP BY vendor
        ORDER BY count DESC
    """)
    rows = cursor.fetchall()
    conn.close()
    return rows


if __name__ == "__main__":
    print("\n" + "="*55)
    print("  Analytics Engine — TEST")
    print("="*55)

    # Summary stats
    print("\n--- Summary Statistics ---")
    stats = get_summary_stats()
    print(f"  Total readings   : {stats['total_readings']}")
    print(f"  Edge decisions   : {stats['edge_decisions']} ({stats['edge_percent']}%)")
    print(f"  Cloud decisions  : {stats['cloud_decisions']}")
    print(f"  Avg confidence   : {stats['avg_confidence']}")
    print(f"  HeartRate avg    : {stats['heart_rate']['avg']} bpm")
    print(f"  SpO2 avg         : {stats['spo2']['avg']}%")
    print(f"  Glucose avg      : {stats['glucose']['avg']} mg/dL")

    # Critical events
    print("\n--- Critical Events (Edge routed) ---")
    events = get_critical_events()
    if events:
        for e in events:
            print(f"  {e[0][:19]} | {e[1]} | HR={e[2]} | SpO2={e[3]} | {e[5][:40]}")
    else:
        print("  No critical events yet")

    # Drift trend
    print("\n--- Drift Detection Trend ---")
    drift = get_drift_trend()
    print(f"  Total logs    : {drift['total_logs']}")
    print(f"  Early avg     : {drift['early_avg']}")
    print(f"  Recent avg    : {drift['recent_avg']}")
    print(f"  Drift count   : {drift['drift_count']}")
    print(f"  Trend         : {drift['trend']}")

    # Vendor breakdown
    print("\n--- Vendor Breakdown ---")
    vendors = get_vendor_breakdown()
    for v in vendors:
        print(f"  {v[0]:<10} : {v[1]} readings")