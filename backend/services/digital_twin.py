from datetime import datetime, timezone

from telemetry.telemetry_client import get_cassandra_session
from agent.resource_manager import (
    CPU_SCALE_UP_THRESHOLD,
    LATENCY_REROUTE_THRESHOLD,
    CPU_SCALE_DOWN_THRESHOLD,
)
from mongo.activity_logs import log_activity

REGIONS = ["Central India", "Korea Central"]
METRICS = {"cpu": "CPU_UTIL", "latency": "LATENCY_MS", "throughput": "THROUGHPUT_RPS"}
REROUTE_SHARE = 0.5  # fraction of load moved to the other region on REROUTE


def read_twin_state():
    """Mirror the latest real telemetry of every region (read only)."""
    cluster, session = get_cassandra_session()
    try:
        session.set_keyspace("gigtrust")
        state = {}
        for region in REGIONS:
            row = {}
            latest_ts = None
            for key, metric in METRICS.items():
                found = session.execute(
                    "SELECT ts, value FROM telemetry_readings "
                    "WHERE region = %s AND metric_type = %s LIMIT 1",
                    (region, metric),
                ).one()
                row[key] = float(found.value) if found else None
                if found and (latest_ts is None or found.ts > latest_ts):
                    latest_ts = found.ts
            row["last_reading"] = latest_ts.isoformat() if latest_ts else None
            state[region] = row
        return state
    finally:
        session.shutdown()
        cluster.shutdown()


def _latency_after(latency0, cpu0, cpu1):
    # Queueing approximation: latency grows as 1 / (1 - utilisation)
    rho0 = min(cpu0 / 100.0, 0.95)
    rho1 = min(cpu1 / 100.0, 0.98)
    return latency0 * (1.0 - rho0) / (1.0 - rho1)


def _predict(cpu, latency, load_multiplier, replicas):
    cpu_new = min(100.0, cpu * load_multiplier / replicas)
    return cpu_new, _latency_after(latency, cpu, cpu_new)


def _decide(region, cpu, latency, alt_region, alt_cpu, alt_latency):
    # Same rules and thresholds as agent/resource_manager.py
    if (cpu >= CPU_SCALE_UP_THRESHOLD and latency >= LATENCY_REROUTE_THRESHOLD
            and alt_cpu is not None and alt_latency is not None
            and alt_cpu < 60.0 and alt_latency < 120.0):
        return "REROUTE", f"{region} is overloaded and {alt_region} is healthier."
    if cpu >= CPU_SCALE_UP_THRESHOLD:
        return "SCALE_UP", f"Predicted CPU {cpu:.0f}% exceeds {CPU_SCALE_UP_THRESHOLD:.0f}%."
    if latency >= LATENCY_REROUTE_THRESHOLD:
        return "REROUTE", f"Predicted latency {latency:.0f} ms exceeds {LATENCY_REROUTE_THRESHOLD:.0f} ms."
    if cpu <= CPU_SCALE_DOWN_THRESHOLD:
        return "SCALE_DOWN", f"Predicted CPU {cpu:.0f}% is below {CPU_SCALE_DOWN_THRESHOLD:.0f}%."
    return "NO_ACTION", "Predicted metrics stay within normal thresholds."


def simulate(region, load_multiplier, replicas=1, cpu=None, latency=None, throughput=None):
    state = read_twin_state()
    if region not in state:
        raise ValueError("Unknown region.")
    alt_region = [r for r in REGIONS if r != region][0]
    now = state[region]
    alt = state[alt_region]

    cpu = cpu if cpu is not None else now["cpu"]
    latency = latency if latency is not None else now["latency"]
    throughput = throughput if throughput is not None else now["throughput"]
    if cpu is None or latency is None or throughput is None:
        raise LookupError("Missing telemetry. Seed it with POST /telemetry/high-load first.")

    # 1. Predict the region under the new load
    p_cpu, p_lat = _predict(cpu, latency, load_multiplier, replicas)
    p_thr = throughput * load_multiplier

    # 2. Ask the agent rules what they would recommend for that predicted state
    action, reason = _decide(region, p_cpu, p_lat, alt_region, alt["cpu"], alt["latency"])

    # 3. Predict the state after that action
    after = {"region_cpu": p_cpu, "region_latency": p_lat, "replicas": replicas,
             "alt_cpu": alt["cpu"], "alt_latency": alt["latency"]}
    if action == "SCALE_UP":
        c, l = _predict(cpu, latency, load_multiplier, replicas + 1)
        after.update(region_cpu=c, region_latency=l, replicas=replicas + 1)
    elif action == "SCALE_DOWN" and replicas > 1:
        c, l = _predict(cpu, latency, load_multiplier, replicas - 1)
        after.update(region_cpu=c, region_latency=l, replicas=replicas - 1)
    elif action == "REROUTE" and alt["cpu"] is not None and alt["latency"] is not None:
        c, l = _predict(cpu, latency, load_multiplier * (1 - REROUTE_SHARE), replicas)
        moved = min(100.0, alt["cpu"] + cpu * load_multiplier * REROUTE_SHARE)
        after.update(region_cpu=c, region_latency=l,
                     alt_cpu=moved, alt_latency=_latency_after(alt["latency"], alt["cpu"], moved))

    result = {
        "region": region,
        "alternate_region": alt_region,
        "load_multiplier": load_multiplier,
        "replicas": replicas,
        "current": {"cpu": cpu, "latency_ms": latency, "throughput_rps": throughput},
        "predicted": {"cpu": round(p_cpu, 1), "latency_ms": round(p_lat, 1),
                      "throughput_rps": round(p_thr, 1)},
        "recommended_action": action,
        "reason": reason,
        "after_action": {k: (round(v, 1) if isinstance(v, float) else v) for k, v in after.items()},
        "model": "Analytic approximation: CPU scales with load per replica, latency follows 1/(1-utilisation). Not a validated simulation.",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    try:
        log_activity(event_type="TWIN_SIMULATION", user_id=0, details=result)
    except Exception:
        pass
    return result
