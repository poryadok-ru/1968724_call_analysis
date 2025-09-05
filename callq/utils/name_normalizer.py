"""
Модуль для автоматической нормализации и сопоставления имен операторов.
"""

import re
from typing import Optional, Dict

def normalize_name(name: str) -> str:
    """
    Нормализует имя для сопоставления:
    - Удаляет лишние пробелы
    - Приводит к нижнему регистру  
    - Удаляет лишние слова (Оператор, Компания, неизвест и т.д.)
    - Оставляет только фамилию и имя
    """
    if not name:
        return ""
    
    # Удаляем лишние слова (должности, титулы, служебные слова)
    unwanted_words = [
        "оператор", "компания", "неизвест", "неизвестн", "неизвестный", "неизвестная",
        "тп", "св", "торговый", "представитель", "ип", "ооо", "зао", "оао",
        "менеджер", "специалист", "консультант", "сотрудник", "работник",
        "младший", "старший", "ведущий", "главный", "заместитель", "помощник",
        "директор", "руководитель", "начальник", "заведующий", "координатор",
        "супервайзер", "супервизор", "куратор", "наставник", "тренер",
        "мл", "ст", "вед", "гл", "зам", "пом", "нач", "зав", "коорд"
    ]
    
    # Разбиваем на слова
    words = re.split(r'\s+', name.strip())
    
    # Фильтруем слова
    filtered_words = []
    for word in words:
        word_clean = re.sub(r'[^\w]', '', word.lower())
        if word_clean and word_clean not in unwanted_words and len(word_clean) > 1:
            filtered_words.append(word_clean)
    
    # Берем первые два слова (фамилия имя)
    return ' '.join(filtered_words[:2])


def find_operator_by_normalized_name(postgres_client, api_name: str) -> Optional[tuple]:
    """
    Находит оператора в БД по нормализованному имени из API.
    
    Args:
        postgres_client: Клиент PostgreSQL
        api_name: Имя оператора из API
        
    Returns:
        Кортеж (id, full_name) или None если не найден
    """
    normalized_api = normalize_name(api_name)
    if not normalized_api:
        return None
    
    try:
        with postgres_client.get_connection() as conn:
            with conn.cursor() as cur:
                # Получаем всех операторов
                cur.execute("SELECT id, full_name FROM operators")
                operators = cur.fetchall()
                
                # Ищем совпадение по нормализованному имени
                for op_id, db_name in operators:
                    normalized_db = normalize_name(db_name)
                    if normalized_api == normalized_db:
                        return (op_id, db_name)
                        
                return None
    except Exception as e:
        print(f"Ошибка поиска оператора: {e}")
        return None


def build_name_cache(postgres_client) -> Dict[str, tuple]:
    """
    Создает кэш нормализованных имен для быстрого поиска.
    
    Returns:
        Словарь {normalized_name: (id, full_name)}
    """
    cache = {}
    try:
        with postgres_client.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT id, full_name FROM operators")
                operators = cur.fetchall()
                
                for op_id, db_name in operators:
                    normalized = normalize_name(db_name)
                    if normalized:
                        cache[normalized] = (op_id, db_name)
                        
    except Exception as e:
        print(f"Ошибка создания кэша: {e}")
        
    return cache


def find_operator_with_cache(cache: Dict[str, tuple], api_name: str) -> Optional[tuple]:
    """
    Быстрый поиск оператора через кэш.
    
    Args:
        cache: Кэш нормализованных имен
        api_name: Имя из API
        
    Returns:
        Кортеж (id, full_name) или None
    """
    normalized = normalize_name(api_name)
    return cache.get(normalized)


if __name__ == "__main__":
    # Тесты нормализации
    test_names = [
        "Беляева Анна",
        "Ольховик Виктория", 
        "Ушаков Сергей",
        "Оператор Компания Малев Сергей Васильевич неизвест",
        "Черникова Екатерина",
        "Сердюкова Маргарита",
        "Санин Валерий"
    ]
    
    print("🔄 Тестирование нормализации имен:")
    for name in test_names:
        normalized = normalize_name(name)
        print(f"   '{name}' -> '{normalized}'")