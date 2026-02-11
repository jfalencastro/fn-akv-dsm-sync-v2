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
    logging.info("Iniciando tentativa de obtenção de Token no DSM")

    try:
        # 1. Obter variáveis de ambiente
        dsm_url = os.environ.get("DSM_BASE_URL", "").strip("/")
        client_id = os.environ.get("DSM_CLIENT_ID")
        client_secret = os.environ.get("DSM_CLIENT_SECRET")

        if not all([dsm_url, client_id, client_secret]):
            logging.error("Erro: Variáveis DSM_BASE_URL, DSM_CLIENT_ID ou DSM_CLIENT_SECRET não configuradas.")
            return

        # 2. Preparar a chamada para /iso/oauth2/token
        token_url = f"{dsm_url}/iso/oauth2/token"
        
        # Dados do formulário (x-www-form-urlencoded)
        auth_params = {
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": client_secret
        }
        encoded_data = urllib.parse.urlencode(auth_params).encode("utf-8")

        logging.info(f"Solicitando token para: {token_url}")

        # 3. Executar a requisição POST
        req = urllib.request.Request(token_url, data=encoded_data, method="POST")
        req.add_header("Content-Type", "application/x-www-form-urlencoded")

        with urllib.request.urlopen(req) as response:
            status = response.getcode()
            body = response.read().decode("utf-8")
            res_json = json.loads(body)
            
            if "access_token" in res_json:
                logging.info(f"Sucesso! Token obtido (Status: {status})")
                # Por segurança, não logue o token inteiro, apenas o início
                logging.info(f"Prefixo do Token: {res_json['access_token'][:10]}...")
            else:
                logging.error(f"Resposta inesperada do DSM: {body}")

    except urllib.error.HTTPError as e:
        logging.error(f"Erro HTTP do DSM ({e.code}): {e.read().decode('utf-8')}")
    except Exception as e:
        logging.exception(f"Erro inesperado: {str(e)}")
