from __future__ import annotations
from typing import List, Optional
from urllib.parse import urljoin

import requests

from callq.models import Autocomplete
from callq.utils import logging, typed_retry
from callq.models.auth import AuthResponse
from callq.models.call import Call
from callq.models.transcription import Transcription
from callq import get_logger


class TBankAPI:
    """
    Клиент TBank API с типизированными моделями.
    
    Пример использования:
        api = TBankAPI()
        auth = api.authenticate("user", "pass")
        calls = api.get_calls_for_day("2025-08-07")
        transcriptions = api.get_transcriptions_for_day("2025-08-07")
    """
    
    BASE_URL = "https://tqm-cloud.tbank.ru"
    
    def __init__(self, timeout: int = 60) -> None:
        """
        Args:
            timeout: Таймаут запросов в секундах
        """
        self.logger = get_logger()
        self._token: Optional[str] = None
        self._timeout = timeout
        self._session = requests.Session()

        self._auth_url = urljoin(self.BASE_URL, "v2/bff-core-app/auth/session-start")
        self._auth_url_old = urljoin(self.BASE_URL, "rest/auth/session-start")
        self._calls_url = urljoin(self.BASE_URL, "v2/bff-communication-search/callsessions")
        self._transcriptions_url = urljoin(self.BASE_URL, "rest/external-voice/transcription/filter")
        self._single_transcription_url = urljoin(self.BASE_URL, "v2/bff-core-app/transcription/segment")
        self._autocomplete_url = urljoin(self.BASE_URL, "v2/bff-core-app/organizational-structures/autocomplete-search")

    def __del__(self):
        if hasattr(self, '_session'):
            self._session.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if hasattr(self, '_session'):
            self._session.close()
    
    def _set_headers(self, with_auth: bool = True) -> None:
        """Установить заголовки для JSON запросов."""
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
        
        if with_auth and self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        
        self._session.headers.update(headers)
    
    @typed_retry(max_attempts=3, delay=1.0)
    @logging()
    def authenticate(self, login: str, password: str, is_old: bool = False) -> AuthResponse:
        """
        Авторизация в TBank API.
        
        Args:
            login: Логин пользователя
            password: Пароль пользователя
            
        Returns:
            AuthResponse модель с токеном
            
        Raises:
            RuntimeError: При ошибке авторизации
        """
        self._set_headers(with_auth=False)
        
        body = {
            "login": login,
            "password": password,
            "authentificationType": "tqm",
            "authSystem": "tqm"
        }

        url = self._auth_url if is_old == False else self._auth_url_old
        response = self._session.post(url, json=body, timeout=self._timeout)
        
        if response.status_code != 200:
            raise RuntimeError(f"Ошибка авторизации: {response.text}")

        data = response.json()
        auth = AuthResponse.from_dict(data)

        self._token = auth.accessToken

        return auth

    @typed_retry(max_attempts=3, delay=1.0)
    @logging()
    def get_autocomplete_search_group(self, term: str, type: str = None, parent_folder_id: str = None) -> Autocomplete:
        """
        Поиск группы/пользователя по названию.
        
        Args:
            term: Строка для поиска
            type: Тип объекта (workGroup, user, etc)
            parent_folder_id: ID родительской папки
            
        Returns:
            Autocomplete модель с найденными элементами
        """
        if not self._token:
            raise RuntimeError("Не авторизован. Вызовите authenticate() сначала")

        self._set_headers(with_auth=True)

        param = {
            "term": term,
            "type": type,
            "parentFolderId": parent_folder_id,
        }

        response = self._session.get(url=self._autocomplete_url, params=param, timeout=self._timeout)
        
        if response.status_code != 200:
            raise RuntimeError(f"Ошибка при поиске группы/пользователя: {response.text}")

        json_data = response.json()
        return Autocomplete.from_dict(json_data)

    
    @typed_retry(max_attempts=3, delay=1.0)
    @logging()
    def get_calls_for_day(self, date: str, filters: dict = None) -> List[Call]:
        """
        Получить список звонков за день.
        
        Args:
            date: Дата в формате "YYYY-MM-DD"
            filters: Дополнительные фильтры (agent, etc). Если None - без фильтров
            
        Returns:
            Список моделей Call
            
        Raises:
            RuntimeError: При ошибке получения данных
        """
        if not self._token:
            raise RuntimeError("Не авторизован. Вызовите authenticate() сначала")
        
        self._set_headers(with_auth=True)
        
        all_calls: List[Call] = []
        page = 1
        
        while page is not None:
            base_filters = {
                "date": {
                    "min": f"{date} 00:00:00",
                    "max": f"{date} 23:59:59",
                }
            }

            if filters:
                base_filters.update(filters)
            
            payload = {
                "filters": base_filters,
                "paging": {
                    "page": page,
                    "itemsPerPage": 1000,
                    "itemsCount": 0
                }
            }
            
            response = self._session.post(self._calls_url, json=payload, timeout=self._timeout)
            
            if response.status_code != 200:
                raise RuntimeError(f"Ошибка получения звонков: {response.text}")
            
            data = response.json()
            items = data.get("items", [])

            for item in items:
                try:
                    call = Call.from_dict(item)
                    all_calls.append(call)
                except Exception as e:
                    self.logger.warning(f"Не удалось распарсить звонок: {e}")
            
            page = data.get("nextPage")

        return all_calls
    
    @typed_retry(max_attempts=3, delay=1.0)
    @logging()
    def get_transcriptions_for_day(self, date: str, operator_id: Optional[str] = None) -> List[Transcription]:
        """
        Получить транскрипции звонков за день.
        
        Args:
            date: Дата в формате "YYYY-MM-DD"
            operator_id: ID оператора (опционально)
            
        Returns:
            Список моделей Transcription
            
        Raises:
            RuntimeError: При ошибке получения данных
        """
        if not self._token:
            raise RuntimeError("Не авторизован. Вызовите authenticate() сначала")
        
        self._set_headers(with_auth=True)
        
        payload = {
            "startDate": f"{date}T00:00:00",
            "endDate": f"{date}T23:59:59",
        }
        
        if operator_id:
            payload["operatorId"] = operator_id
        
        response = self._session.post(self._transcriptions_url, json=payload, timeout=self._timeout)
        
        if response.status_code != 200:
            raise RuntimeError(f"Ошибка получения транскрипций: {response.text}")
        
        data = response.json()
        transcriptions: List[Transcription] = []

        for item in data:
            try:
                transcription = Transcription.from_dict(item)
                transcriptions.append(transcription)
            except Exception as e:
                self.logger.warning(f"Не удалось распарсить транскрипцию: {e}")

        return transcriptions

    def get_transcription_by_call_id(self, call_id: int) -> Transcription:
        """
        Получить транскрипцию конкретного звонка.
        
        Args:
            call_id: ID звонка (smeCallId)
            
        Returns:
            Модель Transcription
            
        Raises:
            RuntimeError: При ошибке получения данных
        """
        if not self._token:
            raise RuntimeError("Не авторизован. Вызовите authenticate() сначала")
        
        self._set_headers(with_auth=True)
        
        response = self._session.post(
            self._single_transcription_url, 
            json={"segmentId": call_id},
            timeout=self._timeout
        )
        
        if response.status_code != 200:
            raise RuntimeError(f"Ошибка получения транскрипции: {response.text}")
        
        data = response.json()
        return Transcription.from_dict(data)