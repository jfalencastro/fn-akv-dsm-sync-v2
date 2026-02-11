import logging
import json
import base64
import os
import requests
import azure.functions as func
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient

app = func.FunctionApp()

# =========================
# Event Grid Trigger
# =========================
@app.function_name(name="akv_dsm_sync")
@app.event_grid_trigger(arg_name="event")
def akv_dsm_sync(event: func.EventGridEvent):

    logging.info("Evento recebido do Event Grid")

    try:
        event_data = event.get_json()
        logging.info(f"Event data: {event_data}")

        secret_name = event_data.get("ObjectName") or event_data.get("objectName")

        if not secret_name:
            logging.error(f"Não foi possível encontrar o nome do objeto no payload: {event_data}")
            return

        # =========================
        # Buscar secret no Key Vault
        # =========================
        vault_url = os.environ["KEYVAULT_URL"]
        credential = DefaultAzureCredential()
        client = SecretClient(vault_url=vault_url, credential=credential)

        secret = client.get_secret(secret_name)
        secret_value = secret.value

        logging.info(f"Secret obtida do AKV: {secret_name}")

        # =========================
        # Montar payload DSM
        # =========================
        secret_object = {
            "key_value": {
                "fields": {
                    "VALUE": secret_value
                }
            }
        }

        encoded_secret = base64.b64encode(
            json.dumps(secret_object).encode("utf-8")
        ).decode("utf-8")

        dsm_payload = {
            "identity": secret_name,
            "name": secret_name,
            "engine": "Generic",
            "expiration_date": "",
            "description": f"Secret sincronizada do AKV: {secret_name}",
            "data": encoded_secret
        }

        logging.info("Payload DSM montado com sucesso")

        # =========================
        # Obter token OAuth2
        # =========================
        dsm_base_url = os.environ["DSM_BASE_URL"]
        client_id = os.environ["DSM_CLIENT_ID"]
        client_secret = os.environ["DSM_CLIENT_SECRET"]

        token_url = f"{dsm_base_url}/iso/oauth2/token"

        token_response = requests.post(
            token_url,
            data={
                "grant_type": "client_credentials",
                "client_id": client_id,
                "client_secret": client_secret
            }
        )

        token_response.raise_for_status()

        access_token = token_response.json()["access_token"]

        logging.info("Token OAuth2 obtido com sucesso")

        # =========================
        # Enviar para DSM
        # =========================
        secret_url = f"{dsm_base_url}/iso/sctm/secret"

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }

        response = requests.post(
            secret_url,
            headers=headers,
            json=dsm_payload
        )

        if response.status_code not in [200, 201]:
            logging.error(f"Erro DSM ({response.status_code}): {response.text}")
            raise Exception("Falha ao criar/atualizar secret no DSM")

        logging.info("Secret enviada com sucesso ao DSM")

    except Exception as e:
        logging.exception("Erro durante processamento da Function")
        raise
