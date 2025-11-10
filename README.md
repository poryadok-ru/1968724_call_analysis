# CallQ — автоматический анализ звонков

## Назначение

CallQ автоматически загружает записи звонков из T-Банк, анализирует их с помощью LLM, сохраняет оценки качества и рекомендации в PostgreSQL и подготавливает данные для дальнейшей BI-аналитики. Проект полностью автоматизирует ночной разбор звонков для нескольких отделов (например, «Торговые представители» и «Офис-менеджеры»).

## Основные возможности

- Загрузка списка звонков и транскрипций из T-Банк API с поддержкой постраничной выборки и повторных попыток.
- Нормализация операторов по справочнику в БД, фильтрация коротких звонков.
- Получение чек-листа критериев и промпта из Google Sheets (через сервисный аккаунт).
- Асинхронный анализ звонков LLM (LiteLLM Gateway) с ретраями, фильтрацией неподходящих диалогов и сбором статистики по токенам.
- Запись результатов в PostgreSQL: оценки, рекомендации, договорённости, причины отказов, транскрипты.
- Готовые Docker Compose файлы для запуска отдельных пайплайнов по отделам.
- Логирование в файлы и stdout, удобные сообщения о ходе обработки (количество звонков, ошибки JSON, пропуски и т. п.).
- Возможность управляющего запуска через cron (см. пример crontab).

## Архитектура и поток данных

### Общая схема работы системы CallQ

```mermaid
graph TB
    %% Внешние сервисы
    GS[Google Sheets<br/>• Критерии оценки<br/>• Промпты<br/>• Токены доступа]
    TB[T-Bank API<br/>• Звонки<br/>• Транскрипты<br/>• Операторы]
    LLM[LLM API<br/>LiteLLM<br/>• Анализ текста<br/>• JSON ответы]

    %% Docker контейнер
    DC[Docker Container<br/>callq-department1/2]

    %% Пайплайн шаги
    C1[1. Get Config<br/>Google Sheets]
    C2[2. Get Calls<br/>T-Bank API]
    C3[3. Analyze<br/>LLM API]
    C4[4. Save to DB<br/>PostgreSQL]

    %% База данных
    DB[(PostgreSQL DB<br/>postgres_callq_data<br/>• calls<br/>• call_transcripts<br/>• call_evaluations<br/>• call_recommendations<br/>• agreements<br/>• call_decline_reasons<br/>• operators, departments<br/>• offices, supervisors)]

    %% Связи внешних сервисов с контейнером
    GS --> DC
    TB --> DC
    LLM --> DC

    %% Поток внутри контейнера
    DC --> C1
    C1 --> C2
    C2 --> C3
    C3 --> C4

    %% Обратные связи к внешним сервисам
    C1 -.-> GS
    C2 -.-> TB
    C3 -.-> LLM

    %% Сохранение в БД
    C4 --> DB

    %% Стилизация
    classDef external fill:#e1f5fe,stroke:#01579b,stroke-width:2px,color:#000000
    classDef container fill:#f3e5f5,stroke:#4a148c,stroke-width:2px,color:#000000
    classDef process fill:#e8f5e8,stroke:#1b5e20,stroke-width:2px,color:#000000
    classDef database fill:#fff3e0,stroke:#e65100,stroke-width:2px,color:#000000

    class GS,TB,LLM external
    class DC container
    class C1,C2,C3,C4 process
    class DB database
```

### Детальный поток данных

`callq/pipelines/daily_run.py` — точка входа пайплайна. Последовательность шагов:

1. Загрузка конфигурации из `.env` (`callq/config.py`).
2. Настройка логгера (`callq/logging_conf.py`).
3. Получение чек-листа критериев и промпт-инструкций из Google Sheets (`callq/pipelines/get_requirements.py`, `callq/clients/google.py`).
4. Получение звонков и транскриптов из T-Банк (`callq/pipelines/get_calls.py`, `callq/clients/t_bank.py`) с фильтрацией операторов по БД.
5. Асинхронный анализ продажных звонков с помощью LLM (`callq/pipelines/call_analysis.py`, `callq/clients/llm.py`).
6. Сохранение всех сущностей в PostgreSQL (`callq/pipelines/save_results_db.py`, `callq/clients/postgres.py`).

### Основные каталоги и файлы

- `callq/clients/` — клиенты для внешних сервисов: Google Sheets, T-Банк, LLM, PostgreSQL.
- `callq/models/` — Pydantic-подобные dataclass-модели для типизированной работы с API и БД.
- `callq/pipelines/` — сценарии пайплайна (получение данных, анализ, сохранение).
- `db/schema.sql` — полная схема БД с созданием всех таблиц, индексов и загрузкой справочников.
- `prompts/` — шаблоны промптов LLM для каждого отдела.
- `docker-compose.department1.yml`, `docker-compose.department2.yml` — готовые конфигурации для запуска отдельных пайплайнов.

## Стек

- Python 3.13 (Dockerfile на базе `python:3.13-alpine`).
- PostgreSQL 15.
- Google Sheets API (service account).
- T-Банк API.
- LiteLLM Gateway (`https://litellm.poryadok.ru`).
- aiohttp, requests, psycopg2-binary, google-api-python-client.

## Подготовка окружения

1. **Клонировать репозиторий** и перейти в каталог `pythonProject1`.
2. **Создать `.env` и `.env.department2`**:  
   ```bash
   cp .env.example .env
   cp .env.example .env.department2
   ```
   Заполните значения (см. таблицу ниже). Для отдела 2 укажите `DEPARTAMENT_ID=2`, собственный `AGENT_GROUP_NAME` и `PROMPT_FILE=./prompts/department2_prompt.txt`.
3. **Поместить файл сервисного аккаунта** Google в `acc_google_api/` и указать путь в `JSON_AUTH`.
4. **Подготовить базу данных**:
   ```bash
   psql postgresql://user:pass@host:port/db -f db/schema.sql
   ```
5. **Установить зависимости для локального запуска (опционально)**: `pip install -r requirements.txt`.

## Переменные окружения

| Переменная | Описание |
|-----------|----------|
| `LOGGING_NAME`, `LOGGING_LEVEL`, `LOGGING_DIR`, `LOGGING_ON_CONSOLE`, `LOGGING_ON_FILE`, `LOGGING_ON_DB` | Настройки логирования. |
| `LOGIN`, `PASSWORD`, `AUTH_TYPE`, `AUTH_SYSTEM` | Доступ к T-Банк API (обычно `tqm`). |
| `AGENT_GROUP_NAME` | Название группы операторов в T-Банк (напр. «Торговые представители»). |
| `JSON_AUTH` | Путь до JSON сервисного аккаунта Google. |
| `REQUIREMENTS_SHEET_ID` | ID Google Spreadsheet с чек-листом и промптом. |
| `REQUIREMENTS_SHEET_NAME_CHECK_LIST` | Название листа с критериями. |
| `REQUIREMENTS_SHEET_NAME_PROMPT_FOR_AI` | Название листа с дополнительными инструкциями. |
| `RESULTS_SHEET_NAME` | Лист для выгрузки результатов (если используется). |
| `APPS_SCRIPT_URL`, `APPS_SCRIPT_FUNCTION` | Параметры запуска Google Apps Script (опционально). |
| `TOKEN_LLM`, `MODEL` | Ключ и модель для LiteLLM. |
| `DATA_BASE` | Строка подключения PostgreSQL (формат `postgresql://user:pass@host:port/db`). |
| `DEPARTAMENT_ID` | ID отдела в таблице `departments` (1, 2, ...). |
| `CHECK_DAY_AGO` | Какая дата берётся относительно «сегодня» (2 = позавчера). |
| `PROMPT_FILE` | Путь к шаблону промпта для отдела. |

## Запуск

### Docker Compose

```bash
docker compose -f docker-compose.department1.yml up --build -d
docker compose -f docker-compose.department2.yml up --build -d
```

Контейнеры читают `.env` / `.env.department2`, берут JSON ключ и промпты из смонтированных директорий и выполняют один проход `daily_run`.  
Если нужно перезапустить другие даты — измените `CHECK_DAY_AGO` и пересоберите контейнер.

### Локальный запуск

```bash
python -m callq.pipelines.daily_run
```

Перед запуском должны быть установлены зависимости и настройки окружения (через `.env` или экспорт переменных).

### Планировщик (пример crontab)

```cron
0 3 * * * cd /opt/callq/callQ && docker-compose -f docker-compose.department1.yml up
10 3 * * * cd /opt/callq/callQ && docker-compose -f docker-compose.department2.yml up
```

Контейнеры завершаются после обработки и выгрузки данных.

## Работа с несколькими отделами

- Для каждого отдела создавайте отдельный `.env` с уникальными значениями `AGENT_GROUP_NAME`, `DEPARTAMENT_ID`, `PROMPT_FILE`.
- Используйте соответствующий `docker-compose.departmentX.yml` или напишите свой сервис в `docker-compose.yml`.
- В БД держите справочник операторов и отделов (см. `db/init.sql`).

## Логи и мониторинг

- Логи приложения пишутся в директорию `logs/` (обновляется каждый день).
- В случае проблем с JSON от LLM включен retry с логированием ошибок.
- Проверяйте таблицу `calls` и связанные, чтобы убедиться, что каскадные удаления работают (`ON DELETE CASCADE`).

## Дополнительные сервисы

- Файлы `prompts/department*.txt` содержат шаблоны сообщений для LLM — при изменении учитывать placeholders `{transcription}`, `{criteria_list}`, `{custom_instructions}`.

## Известные особенности

- Для корректной работы функций с причинами отказов обязательно наличие таблицы `call_decline_reasons`.
- Ответы LLM должны соответствовать JSON-схеме: при ошибках парсинга происходит повторная попытка (до 3 раз).
- `CHECK_DAY_AGO` вычисляется из текущей даты контейнера — при ручном запуске с историческими датами учитывайте время сервера.

## Полезные команды

```bash
docker exec postgres_callq_data \
  psql -U postgres -d postgres \
  -c "SELECT DATE(start_time) AS day, department_id, COUNT(*) \
      FROM calls GROUP BY day, department_id ORDER BY day DESC;"

docker exec postgres_callq_data \
  psql -U postgres -d postgres \
  -c "DELETE FROM calls WHERE start_time::date = '2025-10-20';"
```

## Лицензия

В данный момент лицензия не указана. Если проект будет публиковаться, добавьте выбор лицензии в корень репозитория.
