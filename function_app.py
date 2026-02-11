import logging
import json
import base64
import os
import urllib.request
import urllib.parse
import azure.functions as func

app = func.FunctionApp()

@app.function_name(name="akv_dsm_sync")
@app.event_grid_trigger(arg_name="event")
def akv_dsm_sync(event: func.EventGridEvent):
    logging.info("Evento recebido do Event Grid")

    try:
        event_data = event.get_json()
        secret_name = event_data.get("ObjectName")
        
        if not secret_name:
            logging.error("ObjectName não encontrado no evento.")
            return

        # =========================
        # Obter Configurações
        # =========================
        dsm_base_url = os.environ.get("DSM_BASE_URL")
        client_id = os.environ.get("DSM_CLIENT_ID")
        client_secret = os.environ.get("DSM_CLIENT_SECRET")
        # Nota: Para o Key Vault sem a lib 'azure-keyvault', 
        # precisaríamos de chamadas REST puras. 
        # Vamos focar primeiro em fazer o DSM funcionar com urllib.

        # =========================
        # Obter Token DSM (urllib)
        # =========================
        token_url = f"{dsm_base_url}/iso/oauth2/token"
        auth_data = urllib.parse.urlencode({
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": client_secret
        }).encode("utf-8")

        req_token = urllib.request.Request(token_url, data=auth_data, method="POST")
        with urllib.request.urlopen(req_token) as response:
            res_body = json.loads(response.read().decode("utf-8"))
            access_token = res_body["access_token"]

        logging.info("Token OAuth2 obtido com sucesso via urllib")

        # =========================
        # Enviar para DSM (urllib)
        # =========================
        # (Aqui você montaria o dsm_payload como antes)
        # Exemplo simplificado de envio:
        secret_url = f"{dsm_base_url}/iso/sctm/secret"
        
        # ... lógica do dsm_payload ...

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        # Exemplo de POST JSON com urllib
        # req_dsm = urllib.request.Request(
        #    secret_url, 
        #    data=json.dumps(dsm_payload).encode("utf-8"), 
        #    headers=headers, 
        #    method="POST"
        # )
        
        logging.info("Lógica de envio pronta (urllib)")

    except Exception as e:
        logging.exception(f"Erro: {str(e)}")
