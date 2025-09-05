from typing import Tuple

from callq import get_logger
from callq.clients.google import GoogleSheetsClient
from callq.utils import logging
from callq.models import Criterion, PromptInput


@logging()
def get_requirements(json_path_auth: str, sheet_id: str, sheet_req_name: str, sheet_prompt_name: str) ->  Tuple[list[Criterion], PromptInput]:
    logger = get_logger()

    with GoogleSheetsClient(json_path_auth, sheet_id) as client:
        requirements_data = client.read_range(f"{sheet_req_name}!A:D")
        logger.info(f"Чек-лист из Google Sheet получен")

        categories = Criterion.parse_criterion(requirements_data)
        logger.info(f"Парсинг чек-листа прошел успешно.")

        prompt_data = client.read_range(f"{sheet_prompt_name}!A:B")
        logger.info(f"Промт из Google Sheet получен")

        prompt = PromptInput.from_dict(prompt_data)
        logger.info(f"Парсинг промта прошел успешно")

    return categories, prompt
