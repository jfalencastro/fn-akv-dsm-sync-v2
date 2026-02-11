import logging
import azure.functions as func

app = func.FunctionApp()

@app.function_name(name="teste_basico")
@app.event_grid_trigger(arg_name="event")
def teste_basico(event: func.EventGridEvent):
    logging.info("Evento recebido")
