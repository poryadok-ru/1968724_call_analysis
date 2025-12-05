from typing import List, Any
import requests
import time
import json
import os

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

from callq import get_logger
from callq.utils import typed_retry, logging


class GoogleSheetsClient:
    def __init__(self, credentials_path_or_json: str, sheet_id: str):
        self.logger = get_logger()

        if credentials_path_or_json.strip().startswith('{'):
            credentials_dict = json.loads(credentials_path_or_json)
            credentials = Credentials.from_service_account_info(
                credentials_dict,
                scopes=['https://www.googleapis.com/auth/spreadsheets']
            )
        else:
            credentials = Credentials.from_service_account_file(
                credentials_path_or_json,
                scopes=['https://www.googleapis.com/auth/spreadsheets']
            )

        self.service = build('sheets', 'v4', credentials=credentials)
        self.sheet_id = sheet_id

    def close(self):
        if hasattr(self, 'service'):
            self.service.close()

    def __del__(self):
        self.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    @typed_retry(max_attempts=3, delay=1.0)
    @logging()
    def read_range(self, range_name: str) -> List[List[Any]]:
        result = self.service.spreadsheets().values().get(
            spreadsheetId=self.sheet_id,
            range=range_name
        ).execute()

        return result.get('values', [])

    @typed_retry(max_attempts=3, delay=1.0)
    @logging(with_params=False)
    def append_rows(self, range_name: str, values: List[List[Any]]):
        BATCH_SIZE = 1000
        
        if len(values) <= BATCH_SIZE:
            self.service.spreadsheets().values().append(
                spreadsheetId=self.sheet_id,
                range=range_name,
                valueInputOption='USER_ENTERED',
                body={'values': values}
            ).execute()
        else:
            self.logger.info(f"Разбиваем {len(values)} строк на батчи по {BATCH_SIZE}")
            
            for i in range(0, len(values), BATCH_SIZE):
                batch = values[i:i + BATCH_SIZE]
                self.logger.info(f"Сохраняем батч {i//BATCH_SIZE + 1}: строки {i+1}-{min(i+BATCH_SIZE, len(values))}")
                
                self.service.spreadsheets().values().append(
                    spreadsheetId=self.sheet_id,
                    range=range_name,
                    valueInputOption='USER_ENTERED',
                    body={'values': batch}
                ).execute()


                time.sleep(0.5)

    @typed_retry(max_attempts=3, delay=1.0)
    @logging(with_params=False)
    def update_rows(self, range_name: str, values: List[List[Any]]):
        self.service.spreadsheets().values().update(
            spreadsheetId=self.sheet_id,
            range=range_name,
            valueInputOption='USER_ENTERED',
            body={'values': values}
        ).execute()

    @typed_retry(max_attempts=3, delay=2.0)
    @logging(with_params=False)
    def trigger_apps_script(self, apps_script_url: str, function_name: str = "buildReports") -> bool:
        """Запускает функцию в Google Apps Script"""
        try:
            self.logger.info(f"Запуск функции {function_name} через Apps Script")
            
            response = requests.get(
                apps_script_url,
                params={'action': function_name},
                timeout=300
            )
            
            if response.status_code == 200:
                if response.text.strip().startswith('<!doctype html') or 'accounts.google.com' in response.text:
                    self.logger.error("Apps Script требует аутентификации или не настроен как публичное веб-приложение")
                    return False
                    
                self.logger.info("Отчеты успешно запущены")
                if response.text.strip():
                    self.logger.debug(f"Ответ Apps Script: {response.text[:100]}...")
                return True
            else:
                self.logger.error(f"Ошибка запуска отчетов: HTTP {response.status_code}")
                return False
                
        except Exception as e:
            self.logger.error(f"Ошибка вызова Apps Script: {str(e)}")
            return False



