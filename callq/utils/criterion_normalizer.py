"""
Утилита для нормализации и сопоставления категорий и критериев из ответа LLM
с оригинальными значениями из Excel/Google Sheets.
"""
import re
from typing import List, Dict, Optional, Tuple
from difflib import SequenceMatcher

from callq.models.criterion import Criterion
from callq import get_logger


def normalize_text(text: str) -> str:
    """
    Нормализует текст для сравнения:
    - Убирает лишние пробелы
    - Приводит к нижнему регистру
    - Убирает спецсимволы (кроме букв, цифр и пробелов)
    - Убирает множественные пробелы
    
    Args:
        text: Исходный текст
        
    Returns:
        Нормализованный текст
    """
    if not text:
        return ""
    
    # Приводим к строке и убираем пробелы по краям
    text = str(text).strip()
    
    # Убираем спецсимволы, оставляем только буквы, цифры и пробелы
    text = re.sub(r'[^\w\s]', '', text, flags=re.UNICODE)
    
    # Убираем множественные пробелы
    text = re.sub(r'\s+', ' ', text)
    
    # Приводим к нижнему регистру
    text = text.lower()
    
    return text.strip()


def build_criterion_mapping(criteria: List[Criterion]) -> Dict[Tuple[str, str], Tuple[str, str]]:
    """
    Создает маппинг нормализованных категорий и критериев к оригинальным значениям.
    
    Args:
        criteria: Список оригинальных критериев из Excel
        
    Returns:
        Словарь: (нормализованная_категория, нормализованный_критерий) -> (оригинальная_категория, оригинальный_критерий)
    """
    mapping = {}
    
    for criterion in criteria:
        norm_category = normalize_text(criterion.category)
        norm_indicator = normalize_text(criterion.indicator)
        
        key = (norm_category, norm_indicator)
        value = (criterion.category, criterion.indicator)
        
        mapping[key] = value
    
    return mapping


def find_best_match(
    llm_category: str, 
    llm_criterion: str, 
    mapping: Dict[Tuple[str, str], Tuple[str, str]],
    similarity_threshold: float = 0.85
) -> Optional[Tuple[str, str]]:
    """
    Находит лучшее совпадение для категории и критерия из ответа LLM.
    
    Сначала пытается точное совпадение по нормализованным значениям,
    затем использует fuzzy matching если точного совпадения нет.
    
    Args:
        llm_category: Категория из ответа LLM
        llm_criterion: Критерий из ответа LLM
        mapping: Маппинг нормализованных значений к оригинальным
        similarity_threshold: Минимальный порог схожести для fuzzy matching (0.0-1.0)
        
    Returns:
        Кортеж (оригинальная_категория, оригинальный_критерий) или None если совпадение не найдено
    """
    logger = get_logger()
    
    norm_llm_category = normalize_text(llm_category)
    norm_llm_criterion = normalize_text(llm_criterion)
    
    # Пытаемся найти точное совпадение
    key = (norm_llm_category, norm_llm_criterion)
    if key in mapping:
        return mapping[key]
    
    # Если точного совпадения нет, используем fuzzy matching
    best_match = None
    best_similarity = 0.0
    
    for (norm_cat, norm_crit), (orig_cat, orig_crit) in mapping.items():
        # Вычисляем схожесть категории и критерия отдельно
        cat_similarity = SequenceMatcher(None, norm_llm_category, norm_cat).ratio()
        crit_similarity = SequenceMatcher(None, norm_llm_criterion, norm_crit).ratio()
        
        # Средняя схожесть
        avg_similarity = (cat_similarity + crit_similarity) / 2
        
        if avg_similarity > best_similarity:
            best_similarity = avg_similarity
            best_match = (orig_cat, orig_crit)
    
    if best_similarity >= similarity_threshold:
        # Логируем только если значения изменились (была нормализация)
        if best_match[0] != llm_category or best_match[1] != llm_criterion:
            logger.info(
                f"Нормализация категории/критерия: '{llm_category}' / '{llm_criterion}' -> "
                f"'{best_match[0]}' / '{best_match[1]}' (схожесть: {best_similarity:.2f})"
            )
        return best_match
    else:
        logger.warning(
            f"Не найдено совпадение для категории '{llm_category}' / критерия '{llm_criterion}'. "
            f"Лучшая схожесть: {best_similarity:.2f} (порог: {similarity_threshold}). "
            f"Используются оригинальные значения из LLM."
        )
        # Если не нашли хорошего совпадения, возвращаем нормализованные значения
        # (убираем только лишние пробелы и спецсимволы, но сохраняем регистр)
        clean_category = re.sub(r'\s+', ' ', str(llm_category).strip())
        clean_criterion = re.sub(r'\s+', ' ', str(llm_criterion).strip())
        return (clean_category, clean_criterion)


def normalize_category_and_criterion(
    llm_category: str,
    llm_criterion: str,
    mapping: Dict[Tuple[str, str], Tuple[str, str]]
) -> Tuple[str, str]:
    """
    Нормализует категорию и критерий из ответа LLM, сопоставляя с оригинальными значениями.
    
    Args:
        llm_category: Категория из ответа LLM
        llm_criterion: Критерий из ответа LLM
        mapping: Маппинг нормализованных значений к оригинальным
        
    Returns:
        Кортеж (нормализованная_категория, нормализованный_критерий)
    """
    match = find_best_match(llm_category, llm_criterion, mapping)
    
    if match:
        return match
    else:
        # Fallback: просто очищаем от лишних пробелов
        clean_category = re.sub(r'\s+', ' ', str(llm_category).strip())
        clean_criterion = re.sub(r'\s+', ' ', str(llm_criterion).strip())
        return (clean_category, clean_criterion)


def normalize_category_only(
    llm_category: str,
    mapping: Dict[Tuple[str, str], Tuple[str, str]],
    similarity_threshold: float = 0.85
) -> str:
    """
    Нормализует только категорию из ответа LLM, сопоставляя с оригинальными значениями.
    Используется для рекомендаций, где важен только категория.
    
    Args:
        llm_category: Категория из ответа LLM
        mapping: Маппинг нормализованных значений к оригинальным
        similarity_threshold: Минимальный порог схожести для fuzzy matching
        
    Returns:
        Нормализованная категория
    """
    from difflib import SequenceMatcher
    
    logger = get_logger()
    norm_llm_category = normalize_text(llm_category)
    
    # Собираем уникальные категории из маппинга
    unique_categories = {}
    for (norm_cat, _), (orig_cat, _) in mapping.items():
        if norm_cat not in unique_categories:
            unique_categories[norm_cat] = orig_cat
    
    # Пытаемся найти точное совпадение
    if norm_llm_category in unique_categories:
        return unique_categories[norm_llm_category]
    
    # Если точного совпадения нет, используем fuzzy matching
    best_match = None
    best_similarity = 0.0
    
    for norm_cat, orig_cat in unique_categories.items():
        similarity = SequenceMatcher(None, norm_llm_category, norm_cat).ratio()
        
        if similarity > best_similarity:
            best_similarity = similarity
            best_match = orig_cat
    
    if best_similarity >= similarity_threshold:
        # Логируем только если значение изменилось (была нормализация)
        if best_match != llm_category:
            logger.info(
                f"Нормализация категории: '{llm_category}' -> '{best_match}' "
                f"(схожесть: {best_similarity:.2f})"
            )
        return best_match
    else:
        logger.warning(
            f"Не найдено совпадение для категории '{llm_category}'. "
            f"Лучшая схожесть: {best_similarity:.2f} (порог: {similarity_threshold}). "
            f"Используется оригинальное значение из LLM."
        )
        # Fallback: просто очищаем от лишних пробелов
        return re.sub(r'\s+', ' ', str(llm_category).strip())
