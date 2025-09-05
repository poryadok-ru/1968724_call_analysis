import logging
import os
import sys
from datetime import datetime

def logger_setup(name: str, level: str, log_dir: str, log_to_console: bool, log_to_file: bool, log_to_db: bool) -> logging.Logger:
    global name_logger
    logger = logging.getLogger(name)
    name_logger = name

    if logger.handlers:
        logger.handlers.clear()

    log_level = getattr(logging, level.upper(), logging.INFO)
    logger.setLevel(log_level)

    logger.propagate = False

    formatter = logging.Formatter(
        '%(levelname)s - %(asctime)s - %(name)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    if log_to_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        console_handler.setLevel(log_level)
        logger.addHandler(console_handler)

    if log_to_file:
        try:
            os.makedirs(log_dir, exist_ok=True)

            log_file = os.path.join(log_dir, f"callq_{datetime.now().strftime('%Y%m%d')}.log")
            file_handler = logging.FileHandler(log_file, encoding='utf-8')
            file_handler.setFormatter(formatter)
            file_handler.setLevel(log_level)
            logger.addHandler(file_handler)

            error_file = os.path.join(log_dir, f"callq_errors_{datetime.now().strftime('%Y%m%d')}.log")
            error_handler = logging.FileHandler(error_file, encoding='utf-8')
            error_handler.setFormatter(formatter)
            error_handler.setLevel(logging.ERROR)
            logger.addHandler(error_handler)
            
        except Exception as e:
            if log_to_console:
                logger.warning(f"Не удалось создать файл логов: {e}")
    
    return logger

def get_logger() -> logging.Logger:
    return logging.getLogger(name_logger)

logger = logger_setup('callq', "INFO", './logs', True, False, False)