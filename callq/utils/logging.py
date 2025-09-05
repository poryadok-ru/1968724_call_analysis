from callq import get_logger
from functools import wraps

def logging(with_params=True):
    def deco(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            logger = get_logger()

            safe_kwargs = {}
            for key, value in kwargs.items():
                if 'password' in key.lower() or 'token' in key.lower() or 'secret' in key.lower():
                    safe_kwargs[key] = '***HIDDEN***'
                else:
                    safe_kwargs[key] = value

            try:
                logger.info(f"START {func.__name__}({args}, {safe_kwargs})") if with_params else logger.info(f"START {func.__name__}")
                result = func(*args, **kwargs)
                logger.info(f"SUCCESS {func.__name__}")
                return result

            except Exception as e:
                logger.error(f"FAILED {func.__name__}: {e}", exc_info=True)
                raise

        return wrapper

    return deco


def logging_without_params(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        logger = get_logger()