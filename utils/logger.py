import logging
from datetime import datetime

def setup_logger(name, log_file, level=logging.INFO):
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    handler = logging.FileHandler(log_file)
    handler.setFormatter(formatter)

    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.addHandler(handler)

    return logger

# Основной логгер
main_logger = setup_logger('main', 'logs/main.log')
monitor_logger = setup_logger('monitor', 'logs/monitor.log')
