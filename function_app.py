import logging
import json
import os
import urllib.request
import urllib.parse
import azure.functions as func

app = func.FunctionApp()

@app.function_name(name="akv_dsm_sync")
@app.event_grid_trigger(arg_name="event")
def akv_dsm_sync(event: func.EventGridEvent):
    logging.info("Iniciando Function minima (sem dependencias externas)")

    try:
        # Pega o nome da secret que disparou o evento
        event_data = event.get_json()
        secret_name = event_data.get("ObjectName", "secret-teste-manual")
        
        logging.info(f"Processando para secret: {secret_name}")

        # Configurações do DSM vindas do Portal
        dsm_url = os.environ.get("DSM_BASE_URL", "").strip("/")
        client_id = os.environ.get("DSM_CLIENT_ID")
        client_secret = os.environ.get("DSM_CLIENT_SECRET")

        if not dsm_url or not client_id:
            logging.error("Variaveis de ambiente DSM faltando no Portal!")
            return

        # 1. Obter Token DSM (urllib pura)
        token_url = f"{dsm_url}/iso/oauth2/token"
        auth_params = urllib.parse.urlencode({
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": client_secret
        }).encode("utf-8")

        req_token = urllib.request.Request(token_url, data=auth_params, method="POST")
        with urllib.request.urlopen(req_token) as resp:
            token_res = json.loads(resp.read().decode("utf-8"))
            access_token = token_res["access_token"]

        logging.info("Token DSM obtido com sucesso.")

        # 2. Criar Secret no DSM (Payload Simples/Vazio)
        # Enviando apenas o nome, sem o valor real do AKV por enquanto
        dsm_payload = {
            "identity": secret_name,
            "name": secret_name,
            "engine": "Generic",
            "description": "Teste de integracao sem AKV",
            "data": "eyJrZXlfdmFsdWUiOnsiZmllbGRzIjp7IlZBTFVFIjoicGxhY2Vob2xkZXIifX19" # Payload base64 fixo
        }

        req_dsm = urllib.request.Request(
            f"{dsm_url}/iso/sctm/secret",
            data=json.dumps(dsm_payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            },
            method="POST"
        )

        with urllib.request.urlopen(req_dsm) as resp_dsm:
            logging.info(f"Resposta DSM: {resp_dsm.status}")

    except Exception as e:
        logging.error(f"Erro na execucao: {str(e)}")
