import logging
from pythonjsonlogger import jsonlogger

def setup_json_logger(name=None, level=logging.INFO):
    logger = logging.getLogger(name)
    logHandler = logging.StreamHandler()
    formatter = jsonlogger.JsonFormatter('%(asctime)s %(levelname)s %(message)s', rename_fields={'levelname': 'level'})
    logHandler.setFormatter(formatter)
    if not logger.hasHandlers():
        logger.addHandler(logHandler)
    logger.setLevel(level)
    return logger 