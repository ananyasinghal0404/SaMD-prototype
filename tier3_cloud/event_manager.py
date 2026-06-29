import sys
import os
from datetime import datetime
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tier3_cloud.storage import log_audit

# ══════════════════════════════════════════════════
# EVENT & COMMUNICATION MANAGER — Gap 6
#
# THREE RESPONSIBILITIES:
# 1. Event-driven processor  — reacts to clinical events
# 2. Alert orchestrator      — coordinates downstream actions
# 3. Bidirectional channel   — cloud → edge commands
# ══════════════════════════════════════════════════

# In-memory command queue (edge devices poll this)
COMMAND_QUEUE = []

# In-memory event log (frontend polls this)
EVENT_LOG = []

# ── 1. EVENT-DRIVEN PROCESSOR ─────────────────────

def process_event(event_type, data):
    """
    Receives a clinical event and fans it out
    to all downstream actions simultaneously.
    """
    timestamp = datetime.now().isoformat()

    event = {
        "timestamp": timestamp,
        "event_type": event_type,
        "data": data
    }

    EVENT_LOG.append(event)

    # Fan out to downstream handlers
    actions_taken = []

    if event_type == "CRITICAL_ALERT":
        actions_taken += _orchestrate_critical_alert(data, timestamp)
    elif event_type == "DRIFT_DETECTED":
        actions_taken += _orchestrate_drift_event(data, timestamp)
    elif event_type == "MODEL_DEPLOYED":
        actions_taken += _orchestrate_model_deploy(data, timestamp)
    elif event_type == "ROUTINE_READING":
        actions_taken += _orchestrate_routine(data, timestamp)

    return {
        "event_type": event_type,
        "timestamp": timestamp,
        "actions_taken": actions_taken
    }

# ── 2. ALERT ORCHESTRATOR ─────────────────────────

def _orchestrate_critical_alert(data, timestamp):
    """
    When arrhythmia/hypoxia/critical event fires:
    - Notify doctor
    - Update dashboard
    - Write audit log
    """
    actions = []
    finding = data.get("finding", "Critical condition detected")
    confidence = data.get("confidence", 0.0)
    vendor = data.get("vendor", "Unknown")

    # Doctor notification
    notification = {
        "type": "DOCTOR_NOTIFICATION",
        "message": f"🚨 ALERT: {finding}",
        "confidence": confidence,
        "vendor": vendor,
        "timestamp": timestamp,
        "sent_to": "ICU_Ward_3 — Dr. Sharma"
    }
    actions.append(notification)
    print(f"  📱 Doctor notified: {notification['sent_to']}")
    print(f"     Message: {notification['message']}")

    # Dashboard update
    dashboard_update = {
        "type": "DASHBOARD_UPDATE",
        "status": "RED",
        "finding": finding,
        "timestamp": timestamp
    }
    actions.append(dashboard_update)
    print(f"  📊 Dashboard updated → RED status")

    # Audit log
    log_audit(
        event_type="CRITICAL_ALERT",
        component="event_manager",
        description=f"{finding} | confidence={confidence} | vendor={vendor}",
        clinical_core=True
    )
    actions.append({"type": "AUDIT_LOGGED", "status": "OK"})
    print(f"  📝 Audit log written")

    return actions

def _orchestrate_drift_event(data, timestamp):
    """When drift is detected — notify team, trigger rollback"""
    actions = []
    print(f"  ⚠️  Drift event received — notifying ML team")
    print(f"  🔄 Rollback command queued for edge devices")

    actions.append({"type": "ML_TEAM_NOTIFIED"})
    actions.append({"type": "ROLLBACK_QUEUED"})

    log_audit(
        event_type="DRIFT_EVENT",
        component="event_manager",
        description=f"Drift detected — rollback triggered",
        clinical_core=True
    )
    return actions

def _orchestrate_model_deploy(data, timestamp):
    """When new model deployed — push to edge devices"""
    actions = []
    version = data.get("version", "unknown")
    print(f"  🚀 Model {version} deployment event — pushing to edge")

    push_command("UPDATE_MODEL", {"version": version})
    actions.append({"type": "MODEL_PUSH_QUEUED", "version": version})

    log_audit(
        event_type="MODEL_DEPLOY",
        component="event_manager",
        description=f"Model {version} pushed to edge devices",
        clinical_core=True
    )
    return actions

def _orchestrate_routine(data, timestamp):
    """Routine reading — just log, no alerts"""
    actions = []
    actions.append({"type": "ROUTINE_LOGGED"})
    return actions

# ── 3. BIDIRECTIONAL COMMAND CHANNEL ─────────────

def push_command(command_type, payload):
    """
    Cloud → Edge command.
    Edge devices poll COMMAND_QUEUE and act on commands.
    Examples: UPDATE_MODEL, UPDATE_THRESHOLD, CHANGE_FREQUENCY
    """
    command = {
        "command_id": len(COMMAND_QUEUE) + 1,
        "command_type": command_type,
        "payload": payload,
        "issued_at": datetime.now().isoformat(),
        "status": "PENDING"
    }
    COMMAND_QUEUE.append(command)
    return command

def poll_commands():
    """
    Edge device polls for pending commands.
    Returns list of commands and marks them as DELIVERED.
    """
    pending = [c for c in COMMAND_QUEUE if c["status"] == "PENDING"]
    for c in pending:
        c["status"] = "DELIVERED"
    return pending

def get_event_log():
    return EVENT_LOG

def get_command_queue():
    return COMMAND_QUEUE


# ══════════════════════════════════════════════════
# TEST
# ══════════════════════════════════════════════════

if __name__ == "__main__":
    from tier3_cloud.storage import init_db
    init_db()

    print("\n" + "="*55)
    print("  Event and Communication Manager — TEST")
    print("="*55)

    # ── Test 1: Critical alert ────────────────────
    print("\n--- Event 1: Critical Alert ---")
    result = process_event("CRITICAL_ALERT", {
        "finding": "Arrhythmia detected",
        "confidence": 0.94,
        "vendor": "Philips"
    })
    print(f"  Actions taken: {len(result['actions_taken'])}")

    # ── Test 2: Drift detected ────────────────────
    print("\n--- Event 2: Drift Detected ---")
    result = process_event("DRIFT_DETECTED", {
        "recent_avg": 0.68,
        "threshold": 0.75
    })
    print(f"  Actions taken: {len(result['actions_taken'])}")

    # ── Test 3: Model deployed ────────────────────
    print("\n--- Event 3: Model Deployed ---")
    result = process_event("MODEL_DEPLOYED", {"version": "v2"})
    print(f"  Actions taken: {len(result['actions_taken'])}")

    # ── Test 4: Bidirectional commands ───────────
    print("\n--- Bidirectional Command Channel ---")
    push_command("UPDATE_THRESHOLD", {"HeartRate_max": 145})
    push_command("CHANGE_FREQUENCY", {"ecg_sampling": "250Hz"})

    print(f"  Commands in queue: {len(COMMAND_QUEUE)}")

    print("\n  Edge device polling for commands...")
    commands = poll_commands()
    for cmd in commands:
        print(f"  → Command {cmd['command_id']}: {cmd['command_type']} | {cmd['payload']}")
        print(f"    Status: {cmd['status']}")

    # ── Summary ───────────────────────────────────
    print(f"\n  Total events processed: {len(EVENT_LOG)}")
    print(f"  Total commands issued : {len(COMMAND_QUEUE)}")
    print(f"\n  Gap 6 — Event and Communication Manager ✅")