import json
import asyncio
import aiohttp
import os
from pathlib import Path

from typing import List
from callq import get_logger
from callq.clients.llm import LLM
from callq.models import CallRecord, Criterion, PromptInput
from callq.models.call_analysis_report import CallAnalysisReport
from callq.models.analysis_result import Result, Agreement
from callq.utils import logging

def parse_llm_response(response) -> tuple:
    """Парсит ответ LLM и возвращает данные анализа и количество токенов"""
    logger = get_logger()
    content = response.get_content()

    logger.debug(f"Сырой ответ GPT (первые 500 символов): {content[:500]}")

    if '```json' in content:
        content = content.split('```json')[1].split('```')[0]
    elif '```' in content:
        content = content.split('```')[1].split('```')[0]

    content = content.strip()

    logger.debug(f"После очистки блоков (первые 200 символов): {content[:200]}")

    start = content.find('{')
    end = content.rfind('}')

    if start != -1 and end != -1 and end > start:
        content = content[start:end+1]
    else:
        logger.error(f"Не найден валидный JSON. Start: {start}, End: {end}, Content: {content[:100]}")

    logger.debug(f"Контент для парсинга JSON (первые 200 символов): {content[:200]}")

    try:
        analysis_data = json.loads(content)
    except json.JSONDecodeError as e:
        logger.error(f"Ошибка парсинга JSON: {e}\nКонтент: {content[:500]}")
        raise

    tokens_used = response.get_tokens_used()
    
    return analysis_data, tokens_used



async def analyze_single_call(call: CallRecord, criteria_list: str, custom_instructions: str, 
                             token: str, model: str, prompt_template: str, session: aiohttp.ClientSession, semaphore: asyncio.Semaphore):
    logger = get_logger()
    
    if not call.transcription:
        return None
        
    async with semaphore:
        await asyncio.sleep(0.1)
        logger.info(f"Начинаю анализ звонка {call.segment_id}")

        transcription = formation_of_transcription(call)
        prompt = prompt_template.format(
            transcription=transcription, 
            criteria_list=criteria_list,
            custom_instructions=custom_instructions
        )

        client = LLM(token=token, model=model)
        max_json_retries = 3
        for json_attempt in range(max_json_retries):
            try:
                response = await client.evaluate_call_async(prompt, session)

                analysis_data, tokens_used = parse_llm_response(response)

                if not analysis_data.get('is_sales_call', False):
                    logger.info(f"Звонок {call.call.segmentId} НЕ подходит (токены: {tokens_used}) - пропуск")
                    return None

                analysis_result = Result.from_list(analysis_data)

                report = CallAnalysisReport(
                    call_record=call,
                    analysis_result=analysis_result
                )

                logger.info(f"Звонок {call.call.segmentId} успешно проанализирован: {analysis_result.performance_percentage}% (токены: {tokens_used}), рекомендаций: {len(analysis_result.recommendations)}, договоренности: {len(analysis_result.agreements)}, ")
                return report, tokens_used

            except json.JSONDecodeError as e:
                if json_attempt < max_json_retries - 1:
                    logger.warning(f"JSON ошибка для звонка {call.segment_id}, попытка {json_attempt + 1}/{max_json_retries}: {str(e)}")
                    await asyncio.sleep(1)
                    continue
                else:
                    logger.error(f"JSON ошибка после {max_json_retries} попыток для звонка {call.segment_id}: {str(e)}")
                    return None

            except Exception as e:
                import traceback
                logger.error(f"Ошибка анализа звонка {call.segment_id}: {str(e)}\nТрейсбек:\n{traceback.format_exc()}")
                await asyncio.sleep(1)
                return None

        return None


@logging(with_params=False)
def analyze_calls_async(calls: List[CallRecord], criteria: Criterion, prompt_input: PromptInput, token: str, model: str, prompt_file: str = None, max_concurrent: int = 5) -> List[CallAnalysisReport]:
    """
    Асинхронный анализ звонков с трехуровневой системой оценки и устойчивостью к сбоям.
    
    Анализирует звонки параллельно с помощью LLM API, оценивая качество работы операторов
    по трехуровневой системе критериев:
    - Основные критерии (по этапам звонка)
    - Дополнительные баллы (+5 за каждый)
    - Штрафы (отрицательные баллы)
    
    Включает автоматические retry при сетевых ошибках и таймаутах.
    Обрабатывает только продажные звонки.
    
    Args:
        calls: Список звонков для анализа
        criteria: Критерии оценки качества звонков (3-уровневая структура)
        prompt_input: Дополнительные инструкции для LLM
        token: API ключ для LLM сервиса
        model: Название модели LLM для использования
        max_concurrent: Максимальное количество одновременных запросов
        
    Returns:
        List[CallAnalysisReport]: Список отчетов анализа для продажных звонков
        
    Raises:
        Exception: При критических ошибках после всех retry попыток
    """

    logger = get_logger()
    
    with open(prompt_file, 'r', encoding='utf-8') as f:
        prompt_template = f.read()
    
    logger.info(f"Загружен промпт из: {prompt_file}")

    criteria_list = formation_of_criterion(criteria)
    custom_instructions = formation_additional_conditions(prompt_input)

    async def run_analysis():
        semaphore = asyncio.Semaphore(max_concurrent)

        calls_with_transcription = [call for call in calls if call.transcription]
        logger.info(f"Анализ {len(calls_with_transcription)} звонков (параллельно: {max_concurrent})")
        async with aiohttp.ClientSession() as session:
            tasks = [
                analyze_single_call(call, criteria_list, custom_instructions, token, model, prompt_template, session, semaphore)
                for call in calls_with_transcription
            ]

            results = await asyncio.gather(*tasks, return_exceptions=True)

            successful_results = []
            total_tokens = 0
            filtered_count = 0
            error_count = 0
            
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"Ошибка анализа {calls_with_transcription[i].segment_id}: {str(result)}")
                    error_count += 1
                elif result is None:
                    filtered_count += 1
                    continue
                else:
                    report, tokens_used = result
                    successful_results.append(report)
                    total_tokens += tokens_used
            
            logger.info(f"Анализ завершен:")
            logger.info(f"  - Всего звонков на анализ: {len(calls_with_transcription)}")
            logger.info(f"  - Продажных звонков (успешно): {len(successful_results)}")
            logger.info(f"  - Отфильтровано (не продажные): {filtered_count}")
            logger.info(f"  - Ошибок анализа: {error_count}")
            logger.info(f"  - Использовано токенов: {total_tokens}")
            return successful_results

    return asyncio.run(run_analysis())

def formation_of_criterion(criteria: Criterion) -> str:
    """
    Формирует текстовое представление критериев для LLM промпта.
    
    Преобразует трехуровневую структуру критериев в форматированный текст:
    - Основные критерии с условиями оценки
    - Дополнительные баллы (бонусы) 
    - Штрафы (отрицательные баллы)
    
    Args:
        criteria: Объект Criterion с тремя списками критериев
        
    Returns:
        str: Форматированный текст критериев для передачи в LLM
    """
    result = ""
    for check in criteria:
        result += (f"КАТЕГОРИЯ: {check.category}\n"
                   f"КРИТЕРИЙ: {check.indicator}\n"
                   f"КОММЕНТАРИЙ: {check.comment}\n"    
                   f"МАКСИМАЛЬНЫЙ БАЛЛ: {check.score}\n"
                   f"УСЛОВИЯ ОЦЕНКИ: {check.criteria}\n\n")

    return result

def formation_additional_conditions(prompt: PromptInput) -> str:
    return "\n\n".join(prompt.custom_criteria)


def formation_of_transcription(call: CallRecord) -> str:
    result = ""

    for phrase in call.transcription.phrases:
        result += f"{phrase.channel}: {phrase.text}\n"

    return result


if __name__ == "__main__":
    with open("../../prompts/department2_prompt.txt", 'r', encoding='utf-8') as f:
        prompt_template = f.read()

    prompt = prompt_template.format(
        transcription="transcription",
        criteria_list="criteria_list",
        custom_instructions="custom_instructions"
    )