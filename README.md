# AFL Orchestrator

AI-пайплайны оркестрации мульти-агентных рабочих процессов.

## Быстрый старт

### 1. Установка зависимостей

```bash
make install
```

### 2. Настройка окружения

```bash
cp .env.example .env
# Отредактируйте .env с вашими значениями
```

### 3. Запуск через Docker

```bash
make docker-up
```

Откройте http://localhost:8000/docs для просмотра API документации.

### 4. Локальная разработка

```bash
# Запуск API сервера
make dev

# Запуск тестов
make test

# Линтинг
make lint

# Форматирование кода
make format
```

## Структура проекта

```
afl-orchestrator/
├── src/orchestrator/
│   ├── api/              # REST API endpoints
│   │   ├── routes/       # API route handlers
│   │   └── websockets/   # WebSocket handlers
│   ├── parser/           # AFL config parser
│   ├── engine/           # Workflow engine
│   ├── agent/            # Agent execution
│   ├── services/         # Business logic
│   ├── integrations/     # External integrations
│   ├── storage/          # Database layer
│   │   ├── models/       # SQLAlchemy models
│   │   ├── repositories/ # Data access
│   │   └── migrations/   # Alembic migrations
│   ├── events/           # Event handling
│   └── observability/    # Monitoring & logging
├── tests/
│   ├── unit/             # Unit tests
│   ├── integration/      # Integration tests
│   └── e2e/              # End-to-end tests
├── migrations/           # Database migrations
├── scripts/              # Utility scripts
└── docs/                 # Documentation
```

## Технологии

- **Python 3.12** - основной язык
- **FastAPI** - веб-фреймворк
- **PostgreSQL 15** - база данных
- **Redis 7** - кэш и очереди
- **Celery** - фоновые задачи
- **SQLAlchemy 2.0** - ORM
- **Alembic** - миграции БД
- **MinIO** - хранилище артефактов
- **Docker** - контейнеризация

## Документация

- [Техническое Задание](AFL_Orchestrator_TZ_ADD.md)
- [Архитектура](ARCHITECTURE_DESIGN.md)
- [API Спецификация](API_SPECIFICATION_P1.md)
- [Схема БД](DATABASE_SCHEMA_P1.md)
- [Git Flow](GIT_FLOW.md)
- [Настройка репозитория](REPO_SETUP.md)

## Команды разработки

| Команда          | Описание                |
| ---------------- | ----------------------- |
| `make install`   | Установка зависимостей  |
| `make dev`       | Запуск API сервера      |
| `make test`      | Запуск всех тестов      |
| `make lint`      | Запуск линтеров         |
| `make format`    | Форматирование кода     |
| `make docker-up` | Запуск Docker окружения |
| `make migrate`   | Применение миграций     |

## Лицензия

MIT
