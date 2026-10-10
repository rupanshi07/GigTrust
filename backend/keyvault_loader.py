import os
from dotenv import load_dotenv

load_dotenv()

KEY_VAULT_URL = "https://gigtrust-kv-24262.vault.azure.net/"

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
    # Cloud case: skip Key Vault if every setting is already in the environment
    if all(os.environ.get(v) for v in SECRET_NAME_TO_ENV_VAR.values()):
        print("[Key Vault] All settings already in environment, skipping Key Vault.")
        return

    try:
        from azure.identity import DefaultAzureCredential, InteractiveBrowserCredential
        from azure.keyvault.secrets import SecretClient

        # Try DefaultAzureCredential first (works in Azure with Managed Identity,
        # and also picks up az CLI credentials, environment variables, etc.)
        # Fall back to InteractiveBrowserCredential for local dev.
        try:
            credential = DefaultAzureCredential(exclude_interactive_browser_credential=False)
        except Exception:
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
        print(f"[Key Vault] Unavailable, falling back to environment variables: {e}")


load_secrets_from_key_vault()
