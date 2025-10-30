import os
import time
from typing import List

from callq.clients.t_bank import TBankAPI
from callq.clients.postgres import PostgresClient
from callq.models.transcription import Transcription
from callq.models.call import Call
from callq.models.call_record import CallRecord
from callq.utils.name_normalizer import build_name_cache, find_operator_with_cache

from callq.utils import logging
from callq import get_logger

@logging()
def get_calls(date: str, login: str, password: str, agent_group_name: str = None, postgres_client: PostgresClient = None, min_duration: int = 30) -> List[CallRecord]:
    """
    Получение звонков и транскрипций за день.

    Args:
        date: Дата в формате YYYY-MM-DD
        login: Логин T-Bank
        password: Пароль T-Bank
        agent_group_name: Название группы для фильтрации (опционально)
    
    Returns:
        Список CallRecord с объединенными данными звонков и транскрипций
    """

    logger = get_logger()
    start_time = time.time()
    
    with TBankAPI() as api:
        auth_start = time.time()
        auth = api.authenticate(login, password)
        auth_duration = time.time() - auth_start
        logger.info(f"Авторизован как: {auth.userLogin} (время: {auth_duration:.1f}с)")

        search_start = time.time()
        search_result = api.get_autocomplete_search_group(
            term=agent_group_name
        )
        search_duration = time.time() - search_start
        
        group = search_result.Items[0]
        filters = {
            "agent": [{
                "id": group.id,
                "type": group.type or "workGroup",
                "title": group.name
            }],
            "isNGramSearch": False
        }
        logger.info(f"Найдена группа: '{group.name}' (ID={group.id}) (время: {search_duration:.1f}с)")

        calls_start = time.time()
        calls = api.get_calls_for_day(date, filters)
        calls_duration = time.time() - calls_start
        logger.info(f"Получено звонков: {len(calls)} (время: {calls_duration:.1f}с)")

        if not calls:
            return []

        transcriptions_start = time.time()
        records = []
        filtered_by_duration = 0
        
        logger.info(f"Начинаем получение {len(calls)} транскрипций...")
        for i, call in enumerate(calls, 1):

            if call.duration < min_duration:
                filtered_by_duration += 1
                continue

            trn = api.get_transcription_by_call_id(call.segmentId)
            records.append(CallRecord(call=call, transcription=trn))

            if i % 50 == 0:
                elapsed = time.time() - transcriptions_start
                logger.info(f"Обработано транскрипций: {i}/{len(calls)} (время: {elapsed:.1f}с)")

        transcriptions_duration = time.time() - transcriptions_start
        avg_time_per_transcription = transcriptions_duration / len(calls) if calls else 0
        logger.info(f"Все транскрипции получены за {transcriptions_duration:.1f}с (в среднем {avg_time_per_transcription:.2f}с на транскрипцию)")
        
        if filtered_by_duration > 0:
            logger.info(f"Отфильтровано звонков по длительности (< {min_duration}с): {filtered_by_duration}")

    if postgres_client:
        filter_start = time.time()
        records = filter_operators_from_db(records, postgres_client)
        filter_duration = time.time() - filter_start
        logger.info(f"Фильтрация операторов завершена за {filter_duration:.1f}с")
    
    total_duration = time.time() - start_time
    logger.info(f"ИТОГО: обработка {len(records)} звонков за {total_duration:.1f}с")
    
    return records


@logging(with_params=False)
def filter_operators_from_db(records: List[CallRecord], postgres_client: PostgresClient) -> List[CallRecord]:
    """
    Фильтрует звонки - оставляет только операторов, которые есть в БД.
    Заменяет имена операторов на ID из БД для экономии памяти.
    """
    logger = get_logger()

    name_cache = build_name_cache(postgres_client)
    logger.info(f"Создан кэш операторов из БД: {len(name_cache)}")
    
    filtered_records = []
    found_count = 0
    not_found_operators = set()
    
    for record in records:
        api_name = record.call.operatorUserFullName
        operator_info = find_operator_with_cache(name_cache, api_name)
        
        if operator_info:
            operator_id, db_name = operator_info
            record.call.operatorUserId = operator_id
            record.call.operatorUserFullName = db_name
            filtered_records.append(record)
            found_count += 1
        else:
            not_found_operators.add(api_name)

    logger.info(f"Фильтрация операторов завершена:")
    logger.info(f"  - Звонков с транскрипциями: {len(records)}")
    logger.info(f"  - Операторы найдены в БД: {found_count}")
    logger.info(f"  - Звонки отфильтрованы: {len(records) - found_count}")
    
    if not_found_operators:
        logger.warning(f"Операторы НЕ найдены в БД ({len(not_found_operators)}):")
        for name in sorted(not_found_operators):
            logger.warning(f"  - '{name}'")
    
    return filtered_records


if __name__ == "__main__":
    DATE = "2025-08-07"
    LOGIN = os.environ.get("LOGIN")
    PASSWORD = os.environ.get("PASSWORD")
    AGENT_GROUP_NAME = os.environ.get("AGENT_GROUP_NAME")

    calls = get_calls(
        date=DATE, 
        login=LOGIN, 
        password=PASSWORD, 
        agent_group_name=AGENT_GROUP_NAME
    )