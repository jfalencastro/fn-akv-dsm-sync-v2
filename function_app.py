import logging
import json
import os
import base64
import urllib.request
import urllib.parse
import azure.functions as func

app = func.FunctionApp()

def get_azure_token(resource_url):
    """Obtém um token de acesso usando a Managed Identity da Function App."""
    identity_endpoint = os.environ["IDENTITY_ENDPOINT"]
    identity_header = os.environ["IDENTITY_HEADER"]
    
    # O recurso para Key Vault é sempre https://vault.azure.net
    token_url = f"{identity_endpoint}?resource={urllib.parse.quote(resource_url)}&api-version=2019-08-01"
    
    req = urllib.request.Request(token_url)
    req.add_header("X-IDENTITY-HEADER", identity_header)
    
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))["access_token"]

@app.function_name(name="akv_dsm_sync")
@app.event_grid_trigger(arg_name="event")
def akv_dsm_sync(event: func.EventGridEvent):
    logging.info("Iniciando sincronização nativa (AKV + DSM)")

    try:
        # 1. Extrair dados do Evento
        event_data = event.get_json()
        secret_name = event_data.get("ObjectName")
        vault_url = os.environ.get("KEYVAULT_URL", "").strip("/")
        
        if not secret_name or not vault_url:
            logging.error("Dados insuficientes: Nome da secret ou Vault URL ausentes.")
            return

        # 2. Obter valor da Secret no Key Vault (REST)
        logging.info(f"Buscando secret '{secret_name}' no cofre {vault_url}")
        token_akv = get_azure_token("https://vault.azure.net")
        
        # Endpoint REST: {vault_url}/secrets/{secret_name}?api-version=7.4
        akv_api_url = f"{vault_url}/secrets/{secret_name}?api-version=7.4"
        req_akv = urllib.request.Request(akv_api_url)
        req_akv.add_header("Authorization", f"Bearer {token_akv}")
        
        with urllib.request.urlopen(req_akv) as resp_akv:
            secret_value = json.loads(resp_akv.read().decode("utf-8"))["value"]
            logging.info(f"Sucesso ao ler Secret do AKV")

        # 3. Obter Token no DSM (O que já estava funcionando)
        dsm_base_url = os.environ.get("DSM_BASE_URL", "").strip("/")
        auth_params = urllib.parse.urlencode({
            "grant_type": "client_credentials",
            "client_id": os.environ["DSM_CLIENT_ID"],
            "client_secret": os.environ["DSM_CLIENT_SECRET"]
        }).encode("utf-8")
        
        req_dsm_token = urllib.request.Request(f"{dsm_base_url}/iso/oauth2/token", data=auth_params)
        with urllib.request.urlopen(req_dsm_token) as resp_token:
            dsm_token = json.loads(resp_token.read().decode("utf-8"))["access_token"]

        # 4. Enviar para o DSM
        # Aqui montamos o payload final que o DSM espera
        secret_obj = {"key_value": {"fields": {"VALUE": secret_value}}}
        encoded_payload = base64.b64encode(json.dumps(secret_obj).encode("utf-8")).decode("utf-8")
        
        dsm_payload = {
            "identity": secret_name,
            "name": secret_name,
            "engine": "Generic",
            "data": encoded_payload
        }

        req_push = urllib.request.Request(
            f"{dsm_base_url}/iso/sctm/secret",
            data=json.dumps(dsm_payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {dsm_token}",
                "Content-Type": "application/json"
            },
            method="POST"
        )

        with urllib.request.urlopen(req_push) as resp_final:
            logging.info(f"Sincronização concluída com sucesso! Status DSM: {resp_final.getcode()}")

    except Exception as e:
        logging.exception(f"Falha na sincronização: {str(e)}")
