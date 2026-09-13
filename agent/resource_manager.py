from datetime import datetime, timezone

from telemetry.telemetry_client import (
    get_recent_telemetry,
    get_cassandra_session
)


CPU_SCALE_UP_THRESHOLD = 75.0
LATENCY_REROUTE_THRESHOLD = 180.0
CPU_SCALE_DOWN_THRESHOLD = 30.0


def get_latest_value(region: str, metric_type: str):
    readings = get_recent_telemetry(
        region=region,
        metric_type=metric_type,
        limit=1
    )

    if not readings:
        return None

    return readings[0]["value"]


def log_scaling_action(
    region: str,
    action: str,
    trigger_metric: str,
    trigger_value: float,
    threshold: float
):
    cluster, session = get_cassandra_session()

    try:
        session.set_keyspace("gigtrust")

        query = """
        INSERT INTO scaling_actions (
            region,
            ts,
            action,
            trigger_metric,
            trigger_value,
            threshold
        )
        VALUES (%s, %s, %s, %s, %s, %s)
        """

        session.execute(
            query,
            (
                region,
                datetime.now(timezone.utc),
                action,
                trigger_metric,
                trigger_value,
                threshold
            )
        )

    finally:
        session.shutdown()
        cluster.shutdown()


def make_resource_decision(region: str):
    cpu = get_latest_value(region, "CPU_UTIL")
    latency = get_latest_value(region, "LATENCY_MS")
    throughput = get_latest_value(region, "THROUGHPUT_RPS")

    if cpu is None or latency is None or throughput is None:
        return {
            "status": "insufficient_data",
            "message": "Missing telemetry readings."
        }

    alternate_region = "Korea Central" if region == "Central India" else "Central India"

    alt_cpu = get_latest_value(alternate_region, "CPU_UTIL")
    alt_latency = get_latest_value(alternate_region, "LATENCY_MS")

    # Prefer rerouting if current region is overloaded
    # and alternate region is significantly healthier
    if (
        cpu >= 75.0
        and latency >= 180.0
        and alt_cpu is not None
        and alt_latency is not None
        and alt_cpu < 60.0
        and alt_latency < 120.0
    ):
        action = "REROUTE"
        trigger_metric = "LATENCY_MS"
        trigger_value = latency
        threshold = 180.0

        reason = (
            f"{region} is overloaded with CPU at {cpu}% "
            f"and latency at {latency} ms. "
            f"{alternate_region} is healthier with CPU at "
            f"{alt_cpu}% and latency at {alt_latency} ms."
        )

        target_region = alternate_region

    elif cpu >= 75.0:
        action = "SCALE_UP"
        trigger_metric = "CPU_UTIL"
        trigger_value = cpu
        threshold = 75.0

        reason = (
            f"CPU utilization is {cpu}%, exceeding "
            f"the 75% scale-up threshold."
        )

        target_region = None

    elif latency >= 180.0:
        action = "REROUTE"
        trigger_metric = "LATENCY_MS"
        trigger_value = latency
        threshold = 180.0

        reason = (
            f"Latency is {latency} ms, exceeding "
            f"the 180 ms routing threshold."
        )

        target_region = alternate_region

    elif cpu <= 30.0:
        action = "SCALE_DOWN"
        trigger_metric = "CPU_UTIL"
        trigger_value = cpu
        threshold = 30.0

        reason = (
            f"CPU utilization is {cpu}%, below "
            f"the 30% scale-down threshold."
        )

        target_region = None

    else:
        action = "NO_ACTION"
        trigger_metric = "CPU_UTIL"
        trigger_value = cpu
        threshold = 75.0

        reason = (
            "Infrastructure metrics are within normal operating thresholds."
        )

        target_region = None

    log_scaling_action(
        region=region,
        action=action,
        trigger_metric=trigger_metric,
        trigger_value=trigger_value,
        threshold=threshold
    )

    return {
        "region": region,
        "cpu_util": cpu,
        "latency_ms": latency,
        "throughput_rps": throughput,
        "alternate_region": alternate_region,
        "alternate_cpu": alt_cpu,
        "alternate_latency": alt_latency,
        "decision": action,
        "target_region": target_region,
        "reason": reason
    }
