from callq import get_config, logger_setup
from callq.pipelines import get_calls, get_requirements
from callq.pipelines.call_analysis import analyze_calls_async
from callq.pipelines.save_results_db import save_batch_to_db
from callq.clients.postgres import PostgresClient

from datetime import date, timedelta
import sys
import argparse


def daily_run(target_date: str = None, dry_run: bool = False) -> None:
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

    if target_date:
        # Если дата указана явно, используем её
        check_day = target_date
        logger.info(f"Получаем звонки за указанную дату: {check_day}")
    else:
        # Иначе используем логику CHECK_DAY_AGO
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
        if dry_run:
            logger.info("=" * 80)
            logger.info("РЕЖИМ ТЕСТИРОВАНИЯ (DRY RUN) - результаты НЕ будут сохранены в БД")
            logger.info("=" * 80)
            logger.info(f"Получено {len(results)} результатов анализа")
            
            # Выводим информацию о нормализации категорий и критериев
            normalization_stats = {}
            for report in results:
                if report.analysis_result:
                    for eval_item in report.analysis_result.evaluations:
                        key = f"{eval_item.category} / {eval_item.criterion}"
                        if key not in normalization_stats:
                            normalization_stats[key] = 0
                        normalization_stats[key] += 1
            
            logger.info(f"\nНайдено уникальных категорий/критериев: {len(normalization_stats)}")
            logger.info("\nПримеры категорий и критериев из результатов:")
            for i, (key, count) in enumerate(list(normalization_stats.items())[:10], 1):
                logger.info(f"  {i}. {key} (встречается {count} раз)")
            
            if len(normalization_stats) > 10:
                logger.info(f"  ... и еще {len(normalization_stats) - 10} уникальных комбинаций")
            
            # Выводим примеры результатов
            logger.info("\nПримеры результатов анализа (первые 3):")
            for i, report in enumerate(results[:3], 1):
                logger.info(f"\n  Звонок {i} (ID: {report.call_id}):")
                logger.info(f"    - Производительность: {report.analysis_result.performance_percentage}%")
                logger.info(f"    - Оценок: {len(report.analysis_result.evaluations)}")
                logger.info(f"    - Рекомендаций: {len(report.analysis_result.recommendations)}")
                if report.analysis_result.evaluations:
                    logger.info(f"    - Пример категории/критерия: {report.analysis_result.evaluations[0].category} / {report.analysis_result.evaluations[0].criterion}")
        else:
            save_batch_to_db(postgres_client, results, config.APP.DEPARTAMENT_ID)
            logger.info(f"Сохранено {len(results)} результатов в БД")
    else:
        logger.info("Нет результатов для сохранения")

    logger.info("END WORK")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Запуск анализа звонков')
    parser.add_argument('date', nargs='?', help='Дата для анализа в формате YYYY-MM-DD')
    parser.add_argument('--dry-run', action='store_true', 
                       help='Тестовый режим: выполнить анализ без сохранения в БД')
    
    args = parser.parse_args()
    
    daily_run(target_date=args.date, dry_run=args.dry_run)