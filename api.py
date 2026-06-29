# api.py
# FastAPI server — wraps the entire pipeline
# Exposes REST endpoints + WebSocket for live streaming
#
# Run with: uvicorn api:app --reload
# Access at: http://localhost:8000

import asyncio
import json
from datetime import datetime
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

# ── Import all pipeline modules ───────────────────
from tier1_device.sensor_simulator import generate_reading
from tier1_device.preprocessing import preprocess
from tier1_device.threshold_detector import check_thresholds
from tier2_edge.interoperability_engine import adapt
from tier2_edge.stream_optimizer import StreamOptimizer
from tier2_edge.local_buffer import LocalBuffer
from tier2_edge.orchestration.placement_decision import decide
from tier2_edge.edge_execution import run_local_inference
from tier3_cloud.storage import (
    init_db, save_reading, log_audit,
    log_confidence, get_recent_readings,
    get_audit_trail, get_model_registry,
    seed_model_registry
)
from tier3_cloud.analytics import (
    get_summary_stats, get_critical_events,
    get_drift_trend, get_vendor_breakdown
)
from tier3_cloud.ai_lifecycle import (
    get_all_models, approve_model,
    reject_model, deploy_model,
    rollback, check_drift,
    simulate_federated_round
)
from tier3_cloud.event_manager import (
    process_event, push_command,
    poll_commands, get_event_log,
    get_command_queue
)

# ── App setup ─────────────────────────────────────
app = FastAPI(title="SaMD Prototype API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Pipeline state ────────────────────────────────
optimizer = StreamOptimizer()
buffer    = LocalBuffer(max_size=100)

# ── WebSocket manager ─────────────────────────────
class ConnectionManager:
    def __init__(self):
        self.active = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.active.append(ws)

    def disconnect(self, ws: WebSocket):
        if ws in self.active:
            self.active.remove(ws)

    async def broadcast(self, message: dict):
        for ws in self.active.copy():
            try:
                await ws.send_json(message)
            except Exception:
                self.active.remove(ws)

manager = ConnectionManager()

# ── Startup ───────────────────────────────────────
@app.on_event("startup")
def startup():
    init_db()
    seed_model_registry()
    print("✅ Database initialized")

# ══════════════════════════════════════════════════
# WEBSOCKET — Live pipeline streaming
# ══════════════════════════════════════════════════

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Wait for "start" message from frontend
            data = await websocket.receive_text()
            if data == "start":
                await run_pipeline_ws(websocket)
    except WebSocketDisconnect:
        manager.disconnect(websocket)

async def run_pipeline_ws(websocket: WebSocket):
    """
    Runs one reading through the full pipeline.
    After each step, sends a message to the frontend
    so it can light up the corresponding box.
    """
    async def send(step, status, data={}):
        await websocket.send_json({
            "step": step,
            "status": status,
            "data": data,
            "timestamp": datetime.now().isoformat()
        })
        await asyncio.sleep(0.6)  # pause so frontend can animate

    try:
        # ── STEP 1: Sensor ────────────────────────
        raw = generate_reading()
        await send("sensor", "active", {
            "vendor": raw["vendor"],
            "raw_data": {k: v for k, v in raw.items() if k != "ecg"}
        })

        # ── STEP 2: Preprocessing ─────────────────
        cleaned = preprocess(raw)
        await send("preprocessing", "active", {
            "status": "Noise removed",
            "ecg_cleaned": True
        })

        # ── STEP 3: Threshold Detection ───────────
        checked = check_thresholds(cleaned)
        await send("threshold", "active", {
            "alerts": checked["alert_count"],
            "has_critical": checked["has_critical_alert"],
            "alert_messages": [a["message"] for a in checked["alerts"]]
        })

        # ── STEP 4: Interoperability Engine ───────
        standard = adapt(checked)
        await send("interoperability", "active", {
            "HeartRate": standard.get("HeartRate"),
            "SpO2": standard.get("SpO2"),
            "Glucose": standard.get("Glucose"),
            "Temperature": standard.get("Temperature"),
            "vendor": standard.get("original_vendor"),
            "standardized": True
        })

        # ── STEP 5: Stream Optimizer ──────────────
        opt_result = optimizer.add(standard)
        opt_type = "buffering"
        if opt_result:
            opt_type = opt_result["type"]
        await send("stream_optimizer", "active", {
            "type": opt_type,
            "batch_size": len(optimizer.batch)
        })

        # ── STEP 6: Local Buffer ──────────────────
        buffer.push(standard)
        await send("local_buffer", "active", {
            "queue_size": buffer.size(),
            "stats": buffer.stats()
        })

        # ── STEP 7: Orchestration Engine ─────────
        decision = decide(standard)
        await send("orchestration", "active", {
            "priority": decision["priority"],
            "cpu": decision["cpu_percent"],
            "ram": decision["ram_percent"],
            "network": decision["network_quality"],
            "latency": decision["latency_ms"],
            "decision": decision["decision"],
            "reason": decision["reason"]
        })

        # ── STEP 8: Edge or Cloud ─────────────────
        if decision["decision"] == "EDGE":
            inference = run_local_inference(standard)
            await send("edge_execution", "active", {
                "model": inference["model_version"],
                "confidence": inference["confidence"],
                "findings": inference["findings"],
                "drift_suspected": inference["drift_suspected"]
            })

            # Save to DB
            save_reading(standard, "EDGE", inference)
            log_confidence(inference["model_version"],
                          inference["confidence"],
                          inference["drift_suspected"])
            log_audit("INFERENCE", "edge_execution_engine",
                     f"Confidence={inference['confidence']}",
                     clinical_core=True)

            # Fire event if critical
            if checked["has_critical_alert"]:
                event_result = process_event("CRITICAL_ALERT", {
                    "finding": inference["findings"][0],
                    "confidence": inference["confidence"],
                    "vendor": standard.get("original_vendor")
                })
                await send("event_manager", "active", {
                    "event": "CRITICAL_ALERT",
                    "actions": len(event_result["actions_taken"])
                })

        else:
            fake_inference = {
                "confidence": 0.95,
                "findings": ["Cloud inference complete"],
                "model_version": "cloud_v1",
                "drift_suspected": False
            }
            save_reading(standard, "CLOUD", fake_inference)
            log_audit("INFERENCE", "cloud_layer",
                     "Routine reading — cloud processed",
                     clinical_core=False)
            await send("cloud", "active", {
                "status": "processed",
                "confidence": 0.95
            })

        # ── STEP 9: Done ──────────────────────────
        await send("complete", "done", {
            "decision": decision["decision"],
            "vendor": raw["vendor"]
        })

    except Exception as e:
        await websocket.send_json({
            "step": "error",
            "status": "error",
            "data": {"message": str(e)}
        })

# ══════════════════════════════════════════════════
# REST ENDPOINTS
# ══════════════════════════════════════════════════

@app.get("/")
def root():
    return {"status": "SaMD Prototype API running", "version": "1.0"}

@app.get("/analytics")
def analytics():
    return {
        "summary": get_summary_stats(),
        "critical_events": get_critical_events(),
        "drift_trend": get_drift_trend(),
        "vendor_breakdown": get_vendor_breakdown()
    }

@app.get("/models")
def models():
    rows = get_all_models()
    return [
        {
            "id": r[0], "version": r[1], "status": r[2],
            "accuracy": r[3], "approved_by": r[4],
            "created_at": r[5], "deployed_at": r[6]
        }
        for r in rows
    ]

@app.post("/models/{version}/approve")
def approve(version: str):
    result = approve_model(version)
    return {"message": result}

@app.post("/models/{version}/reject")
def reject(version: str):
    result = reject_model(version)
    return {"message": result}

@app.post("/models/{version}/deploy")
def deploy(version: str):
    result = deploy_model(version)
    return {"message": result}

@app.post("/models/{version}/rollback")
def do_rollback(version: str):
    result = rollback(version)
    return {"message": result}

@app.get("/drift")
def drift():
    return check_drift()

@app.get("/federated")
def federated():
    return simulate_federated_round()

@app.get("/audit")
def audit():
    rows = get_audit_trail(20)
    return [
        {
            "id": r[0], "timestamp": r[1],
            "event_type": r[2], "component": r[3],
            "description": r[4], "clinical_core": r[5]
        }
        for r in rows
    ]

@app.get("/commands")
def commands():
    return get_command_queue()

@app.post("/commands")
def send_command(command_type: str, payload: dict = {}):
    cmd = push_command(command_type, payload)
    return cmd

@app.get("/events")
def events():
    return get_event_log()