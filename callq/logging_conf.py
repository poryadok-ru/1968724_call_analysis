import logging
import os
import sys
from datetime import datetime
from typing import Optional

def logger_setup(name: str, level: str, log_dir: str, log_to_console: bool, log_to_file: bool, log_to_db: bool, logging_token: Optional[str] = None) -> logging.Logger:
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
    
    if log_to_db and logging_token:
        try:
            from log import Log
            remote_logger = Log(token=logging_token, silent_errors=True, timeout=5)
            remote_handler = RemoteLoggingHandler(remote_logger, level=log_level)
            remote_handler.setFormatter(formatter)
            logger.addHandler(remote_handler)
        except ImportError:
            if log_to_console:
                logger.warning("Библиотека poradock-logging не установлена. Удаленное логирование отключено.")
        except Exception as e:
            if log_to_console:
                logger.warning(f"Не удалось настроить удаленное логирование: {e}")
    
    return logger


class RemoteLoggingHandler(logging.Handler):
    """Кастомный handler для отправки логов через poradock-logging API"""
    
    def __init__(self, remote_logger, level=logging.NOTSET):
        super().__init__(level)
        self.remote_logger = remote_logger
        self._status_map = {
            logging.DEBUG: "Debug",
            logging.INFO: "Info",
            logging.WARNING: "Warning",
            logging.ERROR: "Error",
            logging.CRITICAL: "Critical",
        }
    
    def emit(self, record):
        """Отправляет лог на удаленный сервер"""
        try:
            msg = self.format(record)
            status = self._status_map.get(record.levelno, "Info")

            if record.levelno == logging.DEBUG:
                self.remote_logger.debug(msg)
            elif record.levelno == logging.INFO:
                self.remote_logger.info(msg)
            elif record.levelno == logging.WARNING:
                self.remote_logger.warning(msg)
            elif record.levelno == logging.ERROR:
                self.remote_logger.error(msg)
            elif record.levelno == logging.CRITICAL:
                self.remote_logger.critical(msg)
        except Exception:
            self.handleError(record)

def get_logger() -> logging.Logger:
    return logging.getLogger(name_logger)

logger = logger_setup('callq', "INFO", './logs', True, False, False)