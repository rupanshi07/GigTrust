import os
from azure.identity import InteractiveBrowserCredential
from azure.keyvault.secrets import SecretClient

KEY_VAULT_URL = "https://gigtrust-kv-24262.vault.azure.net/"

# Maps Key Vault secret names (hyphens only) to the environment variable
# names the rest of the codebase already expects (underscores). This means
# database.py, auth_users.py, telemetry_client.py etc. need ZERO changes —
# they keep reading os.getenv("SQL_PASSWORD") etc. exactly as before.
SECRET_NAME_TO_ENV_VAR = {
    "SQL-SERVER": "SQL_SERVER",
    "SQL-DATABASE": "SQL_DATABASE",
    "SQL-USERNAME": "SQL_USERNAME",
    "SQL-PASSWORD": "SQL_PASSWORD",
    "MONGO-URI": "MONGO_URI",
    "MONGO-DATABASE": "MONGO_DATABASE",
    "MONGO-COLLECTION": "MONGO_COLLECTION",
    "CASSANDRA-HOST": "CASSANDRA_HOST",
    "CASSANDRA-PORT": "CASSANDRA_PORT",
    "CASSANDRA-USERNAME": "CASSANDRA_USERNAME",
    "CASSANDRA-PASSWORD": "CASSANDRA_PASSWORD",
    "CASSANDRA-KEYSPACE": "CASSANDRA_KEYSPACE",
    "JWT-SECRET-KEY": "JWT_SECRET_KEY",
}


def load_secrets_from_key_vault():
    try:
        credential = InteractiveBrowserCredential()
        client = SecretClient(vault_url=KEY_VAULT_URL, credential=credential)

        loaded = 0
        for secret_name, env_var in SECRET_NAME_TO_ENV_VAR.items():
            try:
                secret = client.get_secret(secret_name)
                os.environ[env_var] = secret.value
                loaded += 1
            except Exception as e:
                print(f"[Key Vault] Could not load '{secret_name}': {e}")

        print(f"[Key Vault] Loaded {loaded}/{len(SECRET_NAME_TO_ENV_VAR)} secrets successfully.")

    except Exception as e:
        print(f"[Key Vault] Could not connect to Key Vault, falling back to .env: {e}")


load_secrets_from_key_vault()