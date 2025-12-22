from dataclasses import dataclass
import os
from pathlib import Path

@dataclass
class Logging:
    LOGGING_NAME: str
    LOGGING_LEVEL: str
    LOGGING_DIR: str
    LOGGING_ON_CONSOLE: bool
    LOGGING_ON_FILE: bool
    LOGGING_ON_DT: bool
    LOGGING_TOKEN: str = None

@dataclass
class TBankConfig:
    LOGIN: str
    PASSWORD: str
    AUTH_TYPE: str
    AUTH_SYSTEM: str

    AGENT_GROUP_NAME: str

@dataclass
class Google:
    JSON_AUTH: str
    REQUIREMENTS_SHEET_ID: str
    REQUIREMENTS_SHEET_NAME_CHECK_LIST: str
    REQUIREMENTS_SHEET_NAME_PROMPT_FOR_AI: str

@dataclass
class LLM:
    TOKEN: str
    MODEL: str

@dataclass
class DataBase:
    URL: str

@dataclass
class App:
    CHECK_DAY_AGO: int
    DEPARTAMENT_ID: int
    PROMPT_FILE: str

@dataclass
class Config:
    LOGGING: Logging
    T_BANK: TBankConfig
    GOOGLE: Google
    LLM_PROXY: LLM
    DATA_BASE: DataBase
    APP: App

def get_config() -> Config:
    """
    Загружает конфигурацию приложения из переменных окружения.
    
    Читает все необходимые настройки для подключения к внешним сервисам:
    - T-Bank API для получения звонков
    - Google Sheets API для критериев и результатов
    - LLM API для анализа звонков
    - Настройки логирования
    
    Returns:
        Config: Объект конфигурации со всеми настройками
        
    Raises:
        KeyError: Если не заданы обязательные переменные окружения
    """
    cnf = Config(
        LOGGING=Logging(
            LOGGING_NAME=os.environ.get("LOGGING_NAME", "callq"),
            LOGGING_LEVEL=os.environ.get("LOGGING_LEVEL", "INFO"),
            LOGGING_DIR=os.environ.get("LOGGING_DIR", "logs"),
            LOGGING_ON_CONSOLE=os.environ.get("LOGGING_ON_CONSOLE", "true").lower() == "true",
            LOGGING_ON_FILE=os.environ.get("LOGGING_ON_FILE", "true").lower() == "true",
            LOGGING_ON_DT=os.environ.get("LOGGING_ON_DT", "true").lower() == "true",
            LOGGING_TOKEN=os.environ.get("LOGGING_TOKEN"),
        ),
        T_BANK=TBankConfig(
            LOGIN=os.environ.get("LOGIN"),
            PASSWORD=os.environ.get("PASSWORD"),
            AUTH_TYPE=os.environ.get("AUTH_TYPE"),
            AUTH_SYSTEM=os.environ.get("AUTH_SYSTEM"),
            AGENT_GROUP_NAME=os.environ.get("AGENT_GROUP_NAME"),
        ),
        GOOGLE=Google(
            JSON_AUTH=os.environ.get("JSON_AUTH"),
            REQUIREMENTS_SHEET_ID=os.environ.get("REQUIREMENTS_SHEET_ID"),
            REQUIREMENTS_SHEET_NAME_CHECK_LIST=os.environ.get("REQUIREMENTS_SHEET_NAME_CHECK_LIST"),
            REQUIREMENTS_SHEET_NAME_PROMPT_FOR_AI=os.environ.get("REQUIREMENTS_SHEET_NAME_PROMPT_FOR_AI"),
        ),
        LLM_PROXY=LLM(
            TOKEN=os.environ.get("TOKEN_LLM"),
            MODEL=os.environ.get("MODEL"),
        ),
        DATA_BASE=DataBase(
            URL=os.environ.get("DATA_BASE"),
        ),
        APP=App(
            CHECK_DAY_AGO=int(os.environ.get("CHECK_DAY_AGO", "2")),
            DEPARTAMENT_ID=int(os.environ.get("DEPARTAMENT_ID", "1")),
            PROMPT_FILE=os.environ.get("PROMPT_FILE")
        )
    )
    
    if not cnf.APP.PROMPT_FILE:
        raise ValueError("PROMPT_FILE не указан в конфигурации")
    
    if not Path(cnf.APP.PROMPT_FILE).exists():
        raise FileNotFoundError(f"Файл промпта не найден: {cnf.APP.PROMPT_FILE}")
    
    return cnf

if __name__ == "__main__":
    config = get_config()
    print(config.LOGGING)
    print(config.T_BANK)