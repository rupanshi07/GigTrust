CREATE KEYSPACE IF NOT EXISTS gigtrust
WITH REPLICATION = {
    'class': 'NetworkTopologyStrategy',
    'datacenter1': 3
};

USE gigtrust;

CREATE TABLE IF NOT EXISTS telemetry_readings (
    region TEXT,
    metric_type TEXT,
    ts TIMESTAMP,
    node_id TEXT,
    value DOUBLE,
    PRIMARY KEY ((region, metric_type), ts)
) WITH CLUSTERING ORDER BY (ts DESC);

CREATE TABLE IF NOT EXISTS scaling_actions (
    region TEXT,
    ts TIMESTAMP,
    action TEXT,
    trigger_metric TEXT,
    trigger_value DOUBLE,
    threshold DOUBLE,
    PRIMARY KEY (region, ts)
) WITH CLUSTERING ORDER BY (ts DESC);