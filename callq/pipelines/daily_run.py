from callq import get_config, logger_setup
from callq.pipelines import get_calls, get_requirements
from callq.pipelines.call_analysis import analyze_calls_async
from callq.pipelines.save_results_db import save_batch_to_db
from callq.clients.postgres import PostgresClient

from datetime import date, timedelta


def daily_run() -> None:
    """
    Основная функция ежедневного анализа качества звонков.
    
    Выполняет следующие шаги:
    1. Получает критерии оценки из Google Sheets
    2. Получает звонки за предыдущий день из T-Bank API
    3. Анализирует звонки с помощью AI 
    4. Сохраняет результаты в Google Sheets
    5. Запускает генерацию отчетов через Apps Script
    """
    
    config = get_config()

    logger = logger_setup(
        name=config.LOGGING.LOGGING_NAME,
        level=config.LOGGING.LOGGING_LEVEL,
        log_dir=config.LOGGING.LOGGING_DIR,
        log_to_console=config.LOGGING.LOGGING_ON_CONSOLE,
        log_to_file=config.LOGGING.LOGGING_ON_FILE,
        log_to_db=config.LOGGING.LOGGING_ON_DT
    )

    logger.info("START WORK")

    requirements, complementary_criteria = get_requirements(
        config.GOOGLE.JSON_AUTH,
        config.GOOGLE.REQUIREMENTS_SHEET_ID,
        config.GOOGLE.REQUIREMENTS_SHEET_NAME_CHECK_LIST,
        config.GOOGLE.REQUIREMENTS_SHEET_NAME_PROMPT_FOR_AI
    )

    postgres_client = PostgresClient(config.DATA_BASE.URL)

    date_now = date.today() - timedelta(days=config.APP.CHECK_DAY_AGO)

    check_day = date_now.strftime("%Y-%m-%d")
    logger.info(f"Получаем звонки за {check_day}")

    daily_calls = get_calls(
        check_day,
        config.T_BANK.LOGIN,
        config.T_BANK.PASSWORD,
        agent_group_name=config.T_BANK.AGENT_GROUP_NAME,
        postgres_client=postgres_client
    )

    logger.info(f"Всего получено звонков после фильтрации: {len(daily_calls)}")

    results = analyze_calls_async(
        calls=daily_calls,
        criteria=requirements,
        prompt_input=complementary_criteria,
        token=config.LLM_PROXY.TOKEN,
        model=config.LLM_PROXY.MODEL,
        prompt_file=config.APP.PROMPT_FILE,
        max_concurrent=3
    )

    if results:
        save_batch_to_db(postgres_client, results, config.APP.DEPARTAMENT_ID)
        logger.info(f"Сохранено {len(results)} результатов в БД")
    else:
        logger.info("Нет результатов для сохранения")

    logger.info("END WORK")

if __name__ == '__main__':
    daily_run()