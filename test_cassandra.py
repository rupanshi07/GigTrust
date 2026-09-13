import os, ssl
import certifi
from cassandra.cluster import Cluster
from cassandra.auth import PlainTextAuthProvider
from cassandra.policies import DCAwareRoundRobinPolicy
from dotenv import load_dotenv

load_dotenv()

auth_provider = PlainTextAuthProvider(
    username=os.getenv("CASSANDRA_USERNAME"),
    password=os.getenv("CASSANDRA_PASSWORD"),
)

ssl_opts = {
    "ca_certs": certifi.where(),
    "ssl_version": ssl.PROTOCOL_TLSv1_2,
}

cluster = Cluster(
    [os.getenv("CASSANDRA_HOST")],
    port=int(os.getenv("CASSANDRA_PORT")),
    auth_provider=auth_provider,
    ssl_options=ssl_opts,
    load_balancing_policy=DCAwareRoundRobinPolicy(local_dc="Central India"),
    protocol_version=4,
)

session = cluster.connect()
print("Connected!")
session.execute(
    f"CREATE KEYSPACE IF NOT EXISTS {os.getenv('CASSANDRA_KEYSPACE')} "
    f"WITH REPLICATION = {{'class': 'NetworkTopologyStrategy', 'Central India': 1}}"
)
print("Keyspace ready.")
cluster.shutdown()