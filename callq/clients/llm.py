from urllib.parse import urljoin
import asyncio
import aiohttp

import requests
from requests import Session

from callq.models import LLMResponse
from callq.utils import logging, typed_retry
from callq import get_logger


class LLM:
    BASE_URL = "https://litellm.poryadok.ru"
    ROLE_USER = "user"

    def __init__(self, token: str, model: str) -> None:
        self._token = token
        self._model = model
        self._endpoint_completions = urljoin(self.BASE_URL, "/v1/chat/completions")
        self._session = Session()

    def __del__(self):
        if hasattr(self, '_session'):
            self._session.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if hasattr(self, '_session'):
            self._session.close()

    def _set_header(self) -> None:
        self._session.headers.update({"Authorization": f"Bearer {self._token}"})

    @typed_retry(max_attempts=3, delay=1.0)
    @logging(with_params=False)
    def evaluate_call(self, prompt: str) -> LLMResponse:
        """
        Отправляет промпт в LLM и возвращает типизированный ответ
        
        Args:
            prompt: Текст промпта для анализа
            
        Returns:
            LLMResponse объект с полной информацией об ответе
        """
        msg = {
            "role": self.ROLE_USER,
            "content": prompt,
        }

        json = {
            "model": self._model,
            "messages": [msg]
        }

        self._set_header()

        max_retries = 3
        base_delay = 5.0
        
        for attempt in range(max_retries):
            try:
                response = self._session.post(
                    self._endpoint_completions, 
                    json=json,
                    timeout=360
                )

                if response.status_code == requests.codes.ok:
                    data = response.json()
                    return LLMResponse.from_dict(data)

                elif response.status_code == 429:
                    # Rate limit - большая задержка
                    if attempt < max_retries - 1:
                        delay = 60.0
                        print(f"Rate limit 429, попытка {attempt + 1}/{max_retries}, ждем {delay}с")
                        import time
                        time.sleep(delay)
                        continue
                    else:
                        raise RuntimeError(f"Rate limit после {max_retries} попыток: {response.status_code} {response.text}")
                
                elif 500 <= response.status_code < 600:
                    if attempt < max_retries - 1:
                        delay = 60.0
                        print(f"Серверная ошибка {response.status_code}, попытка {attempt + 1}/{max_retries}, ждем {delay}с")
                        import time
                        time.sleep(delay)
                        continue
                    else:
                        raise RuntimeError(f"Серверная ошибка после {max_retries} попыток: {response.status_code} {response.text}")

                elif response.status_code >= 400:
                    # Любая другая клиентская ошибка - 60 секунд задержка
                    if attempt < max_retries - 1:
                        delay = 60.0
                        print(f"Клиентская ошибка {response.status_code}, попытка {attempt + 1}/{max_retries}, ждем {delay}с")
                        import time
                        time.sleep(delay)
                        continue
                    else:
                        raise RuntimeError(f"Ошибка клиента: {response.status_code} {response.text}")
                    
            except (requests.exceptions.Timeout, requests.exceptions.ConnectionError, requests.exceptions.RequestException) as e:
                if attempt < max_retries - 1:
                    delay = 60.0
                    print(f"Сетевая ошибка: {str(e)}, попытка {attempt + 1}/{max_retries}, ждем {delay}с")
                    import time
                    time.sleep(delay)
                    continue
                else:
                    raise RuntimeError(f"Сетевая ошибка после {max_retries} попыток: {str(e)}")
        
        raise RuntimeError("Неожиданный выход из цикла retry")

    @logging(with_params=False)
    async def evaluate_call_async(self, prompt: str, session: aiohttp.ClientSession) -> LLMResponse:
        """
        Асинхронно отправляет промпт в LLM с retry логикой
        """
        msg = {
            "role": self.ROLE_USER,
            "content": prompt,
        }

        json_data = {
            "model": self._model,
            "messages": [msg]
        }

        headers = {"Authorization": f"Bearer {self._token}"}

        max_retries = 3
        base_delay = 5.0
        
        for attempt in range(max_retries):
            try:
                timeout = aiohttp.ClientTimeout(total=300)
                async with session.post(
                    self._endpoint_completions, 
                    json=json_data, 
                    headers=headers,
                    timeout=timeout
                ) as response:
                    
                    if response.status == 200:
                        data = await response.json()
                        
                        if not data.get('choices') or not data['choices'][0].get('message', {}).get('content'):
                            logger = get_logger()
                            logger.error(f"Пустой ответ от LLM API! Status 200, но нет content. Full response: {str(data)[:500]}")
                            raise ValueError("Пустой ответ от LLM API")
                            
                        return LLMResponse.from_dict(data)

                    elif response.status == 429:
                        # Rate limit - большая задержка
                        if attempt < max_retries - 1:
                            delay = 60.0
                            print(f"Rate limit 429, попытка {attempt + 1}/{max_retries}, ждем {delay}с")
                            await asyncio.sleep(delay)
                            continue
                        else:
                            error_text = await response.text()
                            raise RuntimeError(f"Rate limit после {max_retries} попыток: {response.status} {error_text}")
                    
                    elif 500 <= response.status < 600:
                        if attempt < max_retries - 1:
                            delay = 60.0
                            print(f"Серверная ошибка {response.status}, попытка {attempt + 1}/{max_retries}, ждем {delay}с")
                            await asyncio.sleep(delay)
                            continue
                        else:
                            error_text = await response.text()
                            raise RuntimeError(f"Серверная ошибка после {max_retries} попыток: {response.status} {error_text}")

                    elif response.status >= 400:

                        if attempt < max_retries - 1:
                            delay = 60.0
                            error_text = await response.text()
                            print(f"Клиентская ошибка {response.status}, попытка {attempt + 1}/{max_retries}, ждем {delay}с")
                            await asyncio.sleep(delay)
                            continue
                        else:
                            error_text = await response.text()
                            raise RuntimeError(f"Ошибка клиента: {response.status} {error_text}")
                        
            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                if attempt < max_retries - 1:
                    delay = 60.0
                    print(f"Сетевая ошибка: {str(e)}, попытка {attempt + 1}/{max_retries}, ждем {delay}с")
                    await asyncio.sleep(delay)
                    continue
                else:
                    raise RuntimeError(f"Сетевая ошибка после {max_retries} попыток: {str(e)}")
        
        raise RuntimeError("Неожиданный выход из цикла retry")
