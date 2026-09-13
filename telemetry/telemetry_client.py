import os
import ssl

from dotenv import load_dotenv
from cassandra.cluster import Cluster
from cassandra.auth import PlainTextAuthProvider

load_dotenv()

CASSANDRA_HOST = os.getenv("CASSANDRA_HOST")
CASSANDRA_PORT = int(os.getenv("CASSANDRA_PORT", "10350"))
CASSANDRA_USERNAME = os.getenv("CASSANDRA_USERNAME")
CASSANDRA_PASSWORD = os.getenv("CASSANDRA_PASSWORD")


def get_cassandra_session():
    auth_provider = PlainTextAuthProvider(
        username=CASSANDRA_USERNAME,
        password=CASSANDRA_PASSWORD
    )

    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False

    cluster = Cluster(
        [CASSANDRA_HOST],
        port=CASSANDRA_PORT,
        auth_provider=auth_provider,
        ssl_context=ssl_context
    )

    session = cluster.connect()

    return cluster, session


def test_cassandra_connection():
    cluster, session = get_cassandra_session()

    try:
        rows = session.execute(
            "SELECT release_version FROM system.local"
        )

        version = rows.one().release_version

        return {
            "database": "Cosmos DB Cassandra",
            "status": "connected",
            "release_version": version
        }

    finally:
        session.shutdown()
        cluster.shutdown()

from datetime import datetime, timezone


def insert_telemetry(
    region: str,
    metric_type: str,
    node_id: str,
    value: float
):
    cluster, session = get_cassandra_session()

    try:
        session.set_keyspace("gigtrust")

        query = """
        INSERT INTO telemetry_readings (
            region,
            metric_type,
            ts,
            node_id,
            value
        )
        VALUES (%s, %s, %s, %s, %s)
        """

        timestamp = datetime.now(timezone.utc)

        session.execute(
            query,
            (
                region,
                metric_type,
                timestamp,
                node_id,
                value
            )
        )

        return {
            "status": "inserted",
            "region": region,
            "metric_type": metric_type,
            "node_id": node_id,
            "value": value,
            "timestamp": timestamp.isoformat()
        }

    finally:
        session.shutdown()
        cluster.shutdown()


def get_recent_telemetry(
    region: str,
    metric_type: str,
    limit: int = 10
):
    cluster, session = get_cassandra_session()

    try:
        session.set_keyspace("gigtrust")

        query = """
        SELECT
            region,
            metric_type,
            ts,
            node_id,
            value
        FROM telemetry_readings
        WHERE region = %s
          AND metric_type = %s
        LIMIT %s
        """

        rows = session.execute(
            query,
            (
                region,
                metric_type,
                limit
            )
        )

        return [
            {
                "region": row.region,
                "metric_type": row.metric_type,
                "timestamp": row.ts.isoformat(),
                "node_id": row.node_id,
                "value": row.value
            }
            for row in rows
        ]

    finally:
        session.shutdown()
        cluster.shutdown()