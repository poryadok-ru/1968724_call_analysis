import time
from functools import wraps
from typing import TypeVar, Callable, Any
from callq import get_logger

T = TypeVar('T')


def typed_retry(max_attempts: int = 3, delay: float = 1.0):
    """
    Retry декоратор для типизированных методов.
    Повторяет вызов при исключениях, возвращает результат как есть.
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            logger = get_logger()
            last_exception = None
            
            for attempt in range(1, max_attempts + 1):
                try:
                    logger.info(f"Attempt {attempt}: {func.__name__}")
                    result = func(*args, **kwargs)
                    logger.info(f"Success on attempt {attempt}: {func.__name__}")
                    return result
                    
                except Exception as e:
                    last_exception = e
                    logger.warning(f"Attempt {attempt} failed for {func.__name__}: {e}")
                    
                    if attempt < max_attempts:
                        time.sleep(delay)

            logger.error(f"All {max_attempts} attempts failed for {func.__name__}")
            raise last_exception
            
        return wrapper
    return decorator