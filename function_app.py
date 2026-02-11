import logging
import os
import urllib.request
import json
import azure.functions as func

app = func.FunctionApp()

@app.function_name(name="akv_dsm_sync")
@app.event_grid_trigger(arg_name="event")
def akv_dsm_sync(event: func.EventGridEvent):
    logging.info("Function carregada com sucesso!")
    try:
        data = event.get_json()
        logging.info(f"Recebido: {data.get('ObjectName')}")
    except Exception as e:
        logging.error(f"Erro: {e}")
