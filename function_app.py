import logging
import azure.functions as func
import os

app = func.FunctionApp()

@app.function_name(name="akv_dsm_sync")
@app.event_grid_trigger(arg_name="event")
def akv_dsm_sync(event: func.EventGridEvent):
    logging.info("Opa! Se você leu isso, o problema são as libs externas.")
    data = event.get_json()
    logging.info(f"Objeto: {data.get('ObjectName')}")
