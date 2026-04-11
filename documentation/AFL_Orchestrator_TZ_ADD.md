# AFL Orchestrator MVP: Техническое Задание и Архитектурный Дизайн-Документ

**Версия документа**: 1.1 **Дата**: 2026-04-10 **Статус**: Черновик **Автор**:
Ведущий Системный Архитектор

**Changelog v1.1 (AFL-101)**:
- Removed `budget_exceeded` from workflow statuses — now an `error_code`
- Added 7 canonical workflow statuses (added `queued`)
- Added error_code section with retryable/non-retryable classification
- Updated sequence diagram: budget exceeded → `failed` with `error_code: budget_exceeded`
- Updated error handling section with explicit error_code references

---

## Содержание

1. [Обзор Системы (System Overview)](#1-обзор-системы-system-overview)
2. [Архитектура (Architecture)](#2-архитектура-architecture)
3. [Модель Данных (Data Model)](#3-модель-данных-data-model)
4. [API Дизайн (API Specification)](#4-api-дизайн-api-specification)
5. [Компонентная Детализация (Component Specs)](#5-компонентная-детализация-component-specs)
6. [Интеграции (Integrations)](#6-интеграции-integrations)
7. [Безопасность (Security)](#7-безопасность-security)
8. [Развёртывание (Deployment)](#8-развёртывание-deployment)
9. [План Разработки (Development Roadmap)](#9-план-разработки-development-roadmap)
10. [Тестирование (Testing Strategy)](#10-тестирование-testing-strategy)

---

## 1. Обзор Системы (System Overview)

### 1.1 Назначение системы и границы (System Boundaries)

AFL Orchestrator — это система оркестрации мульти-агентных AI-рабочих процессов,
которая исполняет декларативные конфигурации на языке AFL (Agentic Flow
Language). Система управляет жизненным циклом AI-агентов, артефактами,
гардрейлами и бюджетом выполнения.

**Границы системы**:

- **Входные данные**: YAML-конфигурации AFL, описывающие агентов, workflow,
  артефакты, гардрейлы.
- **Выходные данные**: Выполненные задачи, сгенерированные артефакты, логи
  выполнения, метрики затрат.
- **Внутренние процессы**: Парсинг конфигов, управление состоянием workflow,
  выполнение агентов, проверка гардрейлов, учёт бюджета.
- **Внешние зависимости**: LLM-провайдеры (OpenAI, Anthropic), системы контроля
  версий (Git), трекеры задач (Jira), инструменты разработки.

**Вне границ системы**:

- Реализация самих AI-агентов (оркестратор управляет их вызовом и
  взаимодействием).
- Пользовательский интерфейс (MVP — CLI/API).
- Обучение моделей (используются готовые LLM API).

### 1.2 Основные пользователи и их потребности

| Пользователь                     | Роль                                  | Потребности                                                                          |
| -------------------------------- | ------------------------------------- | ------------------------------------------------------------------------------------ |
| **Инженер AI-рабочих процессов** | Создаёт и настраивает AFL-конфиги     | Простой декларативный синтаксис, возможность отладки workflow, мониторинг выполнения |
| **Разработчик агентов**          | Добавляет новых агентов и инструменты | Чёткий API для интеграции, документация, тестовое окружение                          |
| **Оператор системы**             | Запускает и мониторит workflow        | Надёжность, наблюдаемость, алертинг, управление бюджетами                            |
| **Безопасник**                   | Контролирует соблюдение политик       | Аудит действий, гардрейлы, изоляция выполнения                                       |

### 1.3 Ключевые сценарии использования (Use Cases)

**UC-1: Запуск мульти-агентного workflow**

1. Инженер загружает AFL-конфиг в оркестратор.
2. Система валидирует конфиг и инициализирует состояние workflow.
3. Оркестратор последовательно запускает агентов согласно workflow.
4. Каждый агент получает контекст, выполняет задачу, возвращает результат.
5. Гардрейлы проверяют выводы агентов перед передачей следующему агенту.
6. По завершении workflow система сохраняет артефакты и логи.

**UC-2: Мониторинг и отладка**

1. Оператор просматривает текущее состояние выполнения workflow.
2. Система показывает историю действий каждого агента, потраченные токены,
   время.
3. Оператор может приостановить/возобновить workflow, изменить параметры.

**UC-3: Управление бюджетами**

1. Система отслеживает расход токенов по каждому агенту и workflow.
2. При приближении к лимиту отправляется уведомление.
3. При превышении лимита workflow приостанавливается или завершается.

### 1.4 Нефункциональные требования

| Требование             | Описание                                                  | Метрика                                                                |
| ---------------------- | --------------------------------------------------------- | ---------------------------------------------------------------------- |
| **Производительность** | Задержка запуска агента после получения контекста         | < 1 сек (95-й перцентиль)                                              |
| **Масштабируемость**   | Поддержка параллельного выполнения множества workflow     | До 100 одновременных workflow на инстансе                              |
| **Надёжность**         | Восстановление после сбоев без потери данных              | Доступность 99.5%, восстановление состояния workflow после перезапуска |
| **Безопасность**       | Изоляция выполнения кода агентов, защита секретов         | Sandbox-окружение для исполнения, шифрование секретов                  |
| **Наблюдаемость**      | Полное логирование всех действий агентов и системы        | Структурированные логи, интеграция с Prometheus/Grafana                |
| **Расширяемость**      | Возможность добавления новых типов агентов и инструментов | Модульная архитектура, чёткие интерфейсы                               |

### 1.5 Матрица тестируемости требований

| ID          | Требование                                 | Метод тестирования                | Критерий приёмки                               | Инструменты                  |
| ----------- | ------------------------------------------ | --------------------------------- | ---------------------------------------------- | ---------------------------- |
| **NF-01**   | Задержка запуска агента < 1 сек (p95)      | Нагрузочное тестирование          | 95% запросов < 1000 мс                         | Locust/k6, Prometheus        |
| **NF-02**   | До 100 одновременных workflow              | Стресс-тестирование               | 100 workflow без деградации >20%               | k6, Docker Compose           |
| **NF-03**   | Доступность 99.5%                          | Длительное тестирование (72 часа) | Downtime < 21.6 мин за 72 часа                 | Prometheus, Grafana          |
| **NF-04**   | Восстановление состояния после сбоя        | Chaos-тестирование                | 100% workflow возобновляются с последнего шага | Chaos Mesh, pytest           |
| **NF-05**   | Sandbox-окружение для агентов              | Security-тесты на escape          | 0 успешных escape-попыток из 100 тестов        | Docker security scan, pytest |
| **NF-06**   | Шифрование секретов                        | Аудит кода + пентест              | Все секреты зашифрованы AES-256                | HashiCorp Vault, OWASP ZAP   |
| **NF-07**   | Полное логирование действий                | Аудит логов                       | ≥99% действий в audit_log за 24 часа           | ELK Stack, pytest            |
| **NF-08**   | Интеграция с Prometheus/Grafana            | Интеграционное тестирование       | Все метрики доступны в Grafana                 | Grafana API, pytest          |
| **NF-09**   | Модульная архитектура                      | Ревью кода + тест плагина         | Новый агент добавляется за <1 часа работы      | pytest, mypy                 |
| **SEC-01**  | Изоляция кода агентов                      | Тесты на инъекции                 | 0 успешных инъекций из 50 тестов               | pytest, OWASP ZAP            |
| **SEC-02**  | Аудит всех операций                        | Проверка БД                       | 100% операций в audit_log                      | SQL-запросы, pytest          |
| **PERF-01** | LLM response time < 15 сек (p95)           | Нагрузочное тестирование          | 95% ответов < 15000 мс                         | Locust, litellm metrics      |
| **PERF-02** | Git clone < 30 сек для репо ≤100 MB        | Интеграционное тестирование       | 95% клонов < 30 сек                            | pytest, asyncio              |
| **PERF-03** | Guardrail проверка < 100 мс                | Юнит-тесты                        | 95% проверок < 100 мс                          | pytest, asyncio              |
| **CTX-01**  | Сжатие контекста с потерей <10% информации | Валидация качества                | BLEU/ROUGE score ≥0.9                          | pytest, nltk                 |
| **GR-01**   | False positive rate гардрейлов <5%         | Тестирование на датасете          | FP rate < 5% на 1000 примеров                  | pytest, sklearn metrics      |
| **GR-02**   | False negative rate гардрейлов <1%         | Тестирование на датасете          | FN rate < 1% на 1000 примеров                  | pytest, sklearn metrics      |
| **BUD-01**  | Точность учёта токенов ±5%                 | Сверка с провайдером              | Расхождение < 5%                               | pytest, OpenAI API           |
| **BUD-02**  | Блокировка при превышении лимита           | Функциональное тестирование       | 100% блокировок при hard limit                 | pytest, asyncio              |

---

## 2. Архитектура (Architecture)

### 2.1 Высокоуровневая архитектурная диаграмма

```mermaid
graph TB
    subgraph "Внешние системы"
        LLM[LLM-провайдеры<br/>OpenAI/Anthropic]
        VCS[Системы контроля версий<br/>Git]
        TRACKER[Трекеры задач<br/>Jira, GitHub Issues]
        TOOLS[Прочие инструменты]
    end

    subgraph "AFL Orchestrator"
        PARSER[Parser Module]
        ENGINE[Workflow Engine]
        CONTEXT[Context Manager]
        GUARDRAIL[Guardrail Engine]
        BUDGET[Budget Tracker]
        AGENT[Agent Executor]
        STORAGE[(Storage Layer)]

        PARSER --> ENGINE
        ENGINE --> CONTEXT
        ENGINE --> GUARDRAIL
        ENGINE --> BUDGET
        ENGINE --> AGENT
        CONTEXT --> STORAGE
        GUARDRAIL --> STORAGE
        BUDGET --> STORAGE
        AGENT --> STORAGE
    end

    AGENT --> LLM
    AGENT --> VCS
    AGENT --> TRACKER
    AGENT --> TOOLS

    CONFIG[AFL Конфиг] --> PARSER
```

### 2.2 Обоснование выбора технологий

| Компонент            | Технология               | Обоснование                                                                              |
| -------------------- | ------------------------ | ---------------------------------------------------------------------------------------- |
| **Язык реализации**  | Python 3.11+             | Широкая экосистема для AI/ML, асинхронное программирование, богатые библиотеки           |
| **Фреймворк**        | FastAPI                  | Высокая производительность, автоматическая генерация OpenAPI-документации, асинхронность |
| **База данных**      | PostgreSQL + SQLAlchemy  | Надёжность, транзакционность, поддержка JSONB для гибких схем                            |
| **Очереди задач**    | Celery + Redis           | Распределённая обработка, retry-механизмы, масштабируемость                              |
| **Кэширование**      | Redis                    | Быстрый доступ к часто используемым данным (контекст, состояния)                         |
| **Хранилище файлов** | S3-совместимое (MinIO)   | Масштабируемое хранение артефактов                                                       |
| **Контейнеризация**  | Docker + Docker Compose  | Упрощение развёртывания, изоляция окружения                                              |
| **Оркестрация**      | Kubernetes (опционально) | Масштабирование в production                                                             |

### 2.3 Паттерны проектирования

1. **State Machine (Машина состояний)**: Workflow Engine реализует конечный
   автомат для управления состояниями workflow.
2. **Event-Driven Architecture (Событийно-ориентированная)**: Компоненты
   общаются через события (например, "агент завершил задачу", "гардрейл
   нарушен").
3. **Strategy Pattern (Стратегия)**: Различные алгоритмы сжатия контекста,
   проверки гардрейлов, выполнения агентов.
4. **Repository Pattern (Репозиторий)**: Абстракция над слоем хранения для
   работы с сущностями.
5. **Factory Pattern (Фабрика)**: Создание агентов и инструментов на основе
   конфигурации.
6. **Observer Pattern (Наблюдатель)**: Бюджет Tracker наблюдает за событиями
   использования токенов.

### 2.4 Масштабируемость и точки расширения

**Горизонтальное масштабирование**:

- Workflow Engine может запускать несколько экземпляров для обработки
  независимых workflow.
- Agent Executor масштабируется через Celery workers.
- База данных: репликация чтения, шардирование при необходимости.

**Точки расширения**:

1. **Плагины агентов**: Новые типы агентов добавляются через регистрацию
   классов, реализующих интерфейс `IAgent`.
2. **Плагины инструментов**: Инструменты регистрируются через конфигурацию,
   реализуют интерфейс `ITool`.
3. **Адаптеры провайдеров**: Поддержка новых LLM-провайдеров через абстракцию
   `LLMProvider`.
4. **Кастомные гардрейлы**: Пользовательские правила проверки через DSL или
   Python-скрипты.

### 2.5 Детальная архитектура компонентов

#### 2.5.1 Parser Module

- **Ответственность**: Преобразование YAML/JSON AFL-конфигов во внутреннее
  представление, валидация схемы.
- **Входы**: Сырой YAML/JSON конфиг, версия схемы AFL.
- **Выходы**: Структурированный объект `AFLConfig`, список ошибок валидации.
- **Интерфейсы**:
  ```python
  class AFLParser:
      def parse(self, raw_config: str) -> AFLConfig: ...
      def validate(self, config: AFLConfig) -> List[ValidationError]: ...
  ```

#### 2.5.2 Workflow Engine

- **Ответственность**: Управление жизненным циклом workflow, обработка
  состояний, координация выполнения шагов.
- **Входы**: Валидированный AFLConfig, параметры запуска.
- **Выходы**: Состояние выполнения workflow, события выполнения.
- **Интерфейсы**:
  ```python
  class WorkflowEngine:
      async def start_workflow(self, config: AFLConfig) -> WorkflowExecution: ...
      async def pause_workflow(self, execution_id: str): ...
      async def resume_workflow(self, execution_id: str): ...
      async def get_status(self, execution_id: str) -> WorkflowStatus: ...
  ```

#### 2.5.3 Context Manager

- **Ответственность**: Управление контекстом между агентами, сжатие, фильтрация,
  передача.
- **Входы**: Текущий контекст, история взаимодействий, лимиты токенов.
- **Выходы**: Оптимизированный контекст для следующего агента, сводка предыдущих
  шагов.
- **Стратегии**: Summarization, Sliding Window, Key Information Extraction.

#### 2.5.4 Guardrail Engine

- **Ответственность**: Проверка вывода агентов на соответствие правилам
  безопасности и качества.
- **Входы**: Контент для проверки, тип гардрейла, параметры проверки.
- **Выходы**: Результат проверки (pass/fail), сообщение об ошибке,
  модифицированный контент.
- **Типы проверок**: Regex, LLM-as-a-Judge, статический анализ.

#### 2.5.5 Budget Tracker

- **Ответственность**: Учёт токенов и затрат, контроль лимитов, уведомления.
- **Входы**: События использования токенов, цены провайдеров, лимиты.
- **Выходы**: Текущий расход, предупреждения о лимитах, блокировки при
  превышении.
- **Интеграции**: Подписка на события `token_used`, `workflow_started`,
  `workflow_completed`.

#### 2.5.6 Agent Executor

- **Ответственность**: Исполнение агентов, управление инструментами,
  взаимодействие с внешними системами.
- **Входы**: Конфигурация агента, контекст, доступные инструменты.
- **Выходы**: Результат выполнения агента, использованные инструменты, метрики.
- **Плагины**: Регистрация новых типов агентов через `IAgent` интерфейс.

#### 2.5.7 Storage Layer

- **Ответственность**: Сохранение состояния, артефактов, логов, метрик.
- **Компоненты**: PostgreSQL (метаданные), MinIO/S3 (артефакты), Redis (кэш).
- **Схемы**: См. раздел 3 "Модель Данных".

### 2.6 Диаграмма последовательности выполнения workflow с 3 агентами

Сценарий: Запуск workflow с тремя агентами (A → B → C), где каждый агент
проходит проверку гардрейлами и учёт бюджета.

```mermaid
sequenceDiagram
    actor User
    participant API as REST API
    participant Parser as Parser Module
    participant Engine as Workflow Engine
    participant Context as Context Manager
    participant Agent as Agent Executor
    participant Guardrail as Guardrail Engine
    participant Budget as Budget Tracker
    participant Storage as Storage Layer
    participant LLM as External LLM

    Note over User,LLM: Фаза 1: Инициализация Workflow
    User->>API: POST /workflows (AFL конфиг)
    API->>Parser: parse(raw_config)
    Parser-->>API: AFLConfig (валидированный)
    API->>Engine: start_workflow(config)
    Engine->>Storage: create_workflow_execution()
    Storage-->>Engine: execution_id
    Engine-->>API: execution_id
    API-->>User: {execution_id, status: "pending"}

    Note over User,LLM: Фаза 2: Выполнение Агента A
    Engine->>Context: get_context(step_a)
    Context-->>Engine: context_a
    Engine->>Agent: execute_agent(agent_a, context_a)
    Agent->>LLM: chat_completion(messages)
    LLM-->>Agent: response_a
    Agent->>Budget: track_tokens(usage_a)
    Budget-->>Agent: ok
    Agent-->>Engine: result_a

    Engine->>Guardrail: check(result_a, guardrail_a)
    Guardrail-->>Engine: pass
    Engine->>Storage: save_agent_execution(agent_a, result_a)
    Engine->>Storage: update_workflow_state(step_a_complete)

    Note over User,LLM: Фаза 3: Выполнение Агента B
    Engine->>Context: get_context(step_b, include_result_a)
    Context-->>Engine: context_b (со сжатой историей)
    Engine->>Agent: execute_agent(agent_b, context_b)
    Agent->>LLM: chat_completion(messages)
    LLM-->>Agent: response_b
    Agent->>Budget: track_tokens(usage_b)
    Budget-->>Agent: ok
    Agent-->>Engine: result_b

    Engine->>Guardrail: check(result_b, guardrail_b)
    Guardrail-->>Engine: fail (нарушение правила)
    Engine->>Engine: handle_guardrail_violation(block)
    Engine->>Storage: save_guardrail_violation(guardrail_b)
    Engine->>Storage: update_workflow_state(step_b_failed)

    Note over User,LLM: Фаза 4: Обработка ошибки и retry
    Engine->>Engine: apply_retry_policy(step_b)
    Engine->>Agent: execute_agent(agent_b, context_b) [retry]
    Agent->>LLM: chat_completion(messages)
    LLM-->>Agent: response_b_retry
    Agent->>Budget: track_tokens(usage_b_retry)
    Budget->>Budget: check_budget_limit()
    Budget-->>Agent: limit_warning (80%)
    Agent-->>Engine: result_b_retry

    Engine->>Guardrail: check(result_b_retry, guardrail_b)
    Guardrail-->>Engine: pass
    Engine->>Storage: save_agent_execution(agent_b, result_b_retry)
    Engine->>Storage: update_workflow_state(step_b_complete)

    Note over User,LLM: Фаза 5: Выполнение Агента C
    Engine->>Context: get_context(step_c, include_result_b)
    Context-->>Engine: context_c
    Engine->>Agent: execute_agent(agent_c, context_c)
    Agent->>LLM: chat_completion(messages)
    LLM-->>Agent: response_c
    Agent->>Budget: track_tokens(usage_c)
    Budget->>Budget: check_budget_limit()
    Budget-->>Agent: limit_exceeded (block)
    Agent-->>Engine: budget_exceeded_error

    Engine->>Engine: handle_budget_exceeded()
    Engine->>Storage: update_workflow_state(failed, error_code=budget_exceeded)
    Engine->>API: workflow_failed(budget_exceeded)
    API-->>User: webhook / email notification

    Note over User,LLM: Альтернативный сценарий: успешное завершение
    Note left of Budget: Если бюджет не превышен
    Budget-->>Agent: ok
    Agent-->>Engine: result_c
    Engine->>Guardrail: check(result_c, guardrail_c)
    Guardrail-->>Engine: pass
    Engine->>Storage: save_agent_execution(agent_c, result_c)
    Engine->>Storage: update_workflow_state(completed)
    Engine->>API: workflow_completed(results)
    API-->>User: {status: "completed", artifacts: [...]}
```

#### Пояснение к диаграмме последовательности:

1. **Фаза 1: Инициализация**:

   - Пользователь отправляет AFL-конфиг через REST API.
   - Parser валидирует конфиг и возвращает структурированный объект.
   - Workflow Engine создаёт запись выполнения в БД и возвращает ID.

2. **Фаза 2: Агент A**:

   - Workflow Engine запрашивает контекст для первого шага.
   - Agent Executor вызывает LLM с контекстом.
   - Budget Tracker учитывает использованные токены.
   - Guardrail Engine проверяет результат, сохраняется состояние.

3. **Фаза 3: Агент B (с нарушением гардрейла)**:

   - Контекст включает сжатую историю предыдущих шагов.
   - Guardrail обнаруживает нарушение правила, workflow переходит в состояние
     ошибки.

4. **Фаза 4: Retry механизм**:

   - Workflow Engine применяет retry политику (exponential backoff).
   - При повторном выполнении Budget Tracker обнаруживает приближение к лимиту
     (80%), отправляет предупреждение.
   - После успешной проверки гардрейла, состояние обновляется.

5. **Фаза 5: Агент C (превышение бюджета)**:
   - Budget Tracker обнаруживает превышение лимита, блокирует выполнение.
   - Workflow переходит в состояние `failed` с `error_code: budget_exceeded`, отправляются уведомления.
   - Альтернативный сценарий: если бюджет не превышен, workflow завершается
     успешно.

#### Ключевые сообщения между компонентами:

| Сообщение                       | От     | К         | Назначение                   |
| ------------------------------- | ------ | --------- | ---------------------------- |
| `parse(raw_config)`             | API    | Parser    | Валидация AFL конфига        |
| `start_workflow(config)`        | API    | Engine    | Запуск workflow              |
| `get_context(step)`             | Engine | Context   | Получение контекста для шага |
| `execute_agent(agent, context)` | Engine | Agent     | Выполнение агента            |
| `chat_completion(messages)`     | Agent  | LLM       | Вызов LLM API                |
| `track_tokens(usage)`           | Agent  | Budget    | Учёт токенов                 |
| `check(content, guardrail)`     | Engine | Guardrail | Проверка гардрейла           |
| `save_agent_execution()`        | Engine | Storage   | Сохранение результата        |
| `update_workflow_state()`       | Engine | Storage   | Обновление состояния         |

#### Обработка ошибок и восстановление:

1. **Guardrail violation**: Workflow → `failed` с `error_code: guardrail_violation` (non-retryable).
2. **Budget exceeded**: Workflow → `failed` с `error_code: budget_exceeded` (non-retryable).
3. **LLM timeout**: Workflow → `failed` с `error_code: agent_error` (retryable), circuit breaker, fallback на другую модель.
4. **Storage failure**: Retry с exponential backoff, сохранение в кэш Redis.

#### Статусы Workflow

Workflow проходит через следующие состояния в процессе выполнения:

| Статус | Описание | Кто инициирует |
|--------|----------|----------------|
| pending | Создан, ожидает планировщика | Система (после POST /workflows) |
| queued | Запланирован, ожидает исполнителя | Scheduler |
| running | Выполняется | Executor |
| paused | Временно приостановлен | Пользователь |
| completed | Успешно завершён | Система |
| failed | Ошибка выполнения | Система |
| cancelled | Отменён | Пользователь или Система |

#### Причины ошибок (error_code)

При статусе `failed` или `cancelled` поле `error_code` указывает причину:

| Код | Описание | Можно повторить | Действие |
|-----|----------|-----------------|----------|
| guardrail_violation | Нарушение гардрейла безопасности | ❌ Нет | Исправить конфигурацию |
| budget_exceeded | Превышен бюджет токенов | ❌ Нет | Увеличить бюджет |
| agent_error | Ошибка в агенте (таймаут, исключение) | ✅ Да | Система попытается автоматически |
| system_error | Системная ошибка (БД, сеть) | ✅ Да | Система попытается автоматически |
| cancelled_by_user | Отменено пользователем | ❌ Нет | — |

⚠️ **Важно:** `budget_exceeded` — это НЕ статус, а причина ошибки (`error_code`).
Workflow при этом получает статус `failed`.

---

## 3. Модель Данных (Data Model)

### 3.1 Основные сущности

```mermaid
erDiagram
    Project ||--o{ Workflow : contains
    Workflow ||--o{ WorkflowExecution : has_executions
    Workflow ||--o{ AgentDefinition : defines
    Workflow ||--o{ ArtifactDefinition : defines
    Workflow ||--o{ GuardrailDefinition : defines

    WorkflowExecution ||--o{ TaskExecution : consists_of
    TaskExecution ||--o{ AgentExecution : performed_by
    TaskExecution ||--o{ ArtifactVersion : produces
    TaskExecution }o--o{ GuardrailCheck : validated_by

    AgentExecution ||--o{ LLMCall : makes
    AgentExecution ||--o{ ToolCall : uses

    Budget ||--o{ CostRecord : tracks

    Project {
        uuid id PK
        string name
        jsonb config
        timestamp created_at
    }

    Workflow {
        uuid id PK
        uuid project_id FK
        string name
        jsonb afl_config
        timestamp created_at
    }

    WorkflowExecution {
        uuid id PK
        uuid workflow_id FK
        string status
        jsonb current_state
        timestamp started_at
        timestamp finished_at
    }

    AgentExecution {
        uuid id PK
        uuid task_execution_id FK
        uuid agent_definition_id FK
        jsonb input_context
        jsonb output
        integer token_usage
        timestamp executed_at
    }

    ArtifactVersion {
        uuid id PK
        uuid artifact_definition_id FK
        uuid task_execution_id FK
        string storage_path
        jsonb metadata
        timestamp created_at
    }

    GuardrailCheck {
        uuid id PK
        uuid guardrail_definition_id FK
        uuid task_execution_id FK
        boolean passed
        string message
        timestamp checked_at
    }

    CostRecord {
        uuid id PK
        uuid workflow_execution_id FK
        string provider
        string model
        integer tokens
        decimal cost_usd
        timestamp recorded_at
    }
```

### 3.2 Схема хранения конфигов AFL

Конфиги AFL хранятся в виде JSONB в таблице `Workflow`. Пример структуры:

```yaml
# project.yaml
version: "1.0"
project: "Code Review Automation"
budget:
  total_tokens: 100000
  warning_threshold: 0.8

agents:
  - id: "code_analyzer"
    type: "llm"
    model: "gpt-4"
    tools: ["git_clone", "static_analysis"]
    guardrails: ["no_secrets", "code_quality"]

  - id: "reviewer"
    type: "llm"
    model: "claude-3-opus"
    tools: ["jira_comment"]
    guardrails: ["professional_tone"]

artifacts:
  - id: "source_code"
    type: "git_repo"
    url: "https://github.com/org/repo"

  - id: "analysis_report"
    type: "json"
    path: "/reports/analysis.json"

guardrails:
  - id: "no_secrets"
    type: "regex"
    pattern: "(?i)password|api[_-]?key|secret"
    action: "block"

  - id: "code_quality"
    type: "llm_judge"
    prompt: "Оцени качество кода по шкале 1-10"
    threshold: 7

workflow:
  - step: "clone_repo"
    agent: "code_analyzer"
    artifact: "source_code"

  - step: "analyze_code"
    agent: "code_analyzer"
    depends_on: ["clone_repo"]

  - step: "review"
    agent: "reviewer"
    depends_on: ["analyze_code"]
    artifact: "analysis_report"
```

### 3.3 Схема хранения состояния выполнения (execution state)

Состояние выполнения workflow хранится в таблице `WorkflowExecution` в поле
`current_state` (JSONB):

```json
{
  "step": "analyze_code",
  "status": "in_progress",
  "context": {
    "source_code": {
      "commit_hash": "abc123",
      "files_changed": ["src/main.py"]
    }
  },
  "artifacts": {
    "source_code": "s3://bucket/artifacts/uuid1.tar.gz"
  },
  "metrics": {
    "tokens_used": 4500,
    "start_time": "2026-03-30T10:00:00Z"
  }
}
```

### 3.4 Схема хранения истории чатов и контекста

Каждое выполнение агента сохраняется в `AgentExecution` с полями:

- `input_context`: JSON с промптом и контекстом
- `output`: JSON с ответом агента
- `token_usage`: количество использованных токенов

Для длинных диалогов используется отдельная таблица `ConversationTurn`:

```sql
CREATE TABLE conversation_turn (
    id UUID PRIMARY KEY,
    agent_execution_id UUID REFERENCES agent_execution(id),
    role VARCHAR(10), -- 'user', 'assistant', 'system'
    content TEXT,
    tokens INTEGER,
    timestamp TIMESTAMP
);
```

### 3.5 Схема хранения метрик (токены, затраты, время)

Таблица `CostRecord` агрегирует затраты по провайдерам и моделям. Дополнительные
метрики хранятся в таблице `ExecutionMetrics`:

```sql
CREATE TABLE execution_metrics (
    id UUID PRIMARY KEY,
    workflow_execution_id UUID REFERENCES workflow_execution(id),
    metric_name VARCHAR(50), -- 'execution_time', 'tokens_per_step', 'success_rate'
    metric_value DECIMAL,
    timestamp TIMESTAMP
);
```

---

## 4. API Дизайн (API Specification)

### 4.1 Внутреннее API между компонентами оркестратора

Компоненты общаются через шину событий (Redis Pub/Sub) и прямые вызовы методов.

**События**:

```python
class WorkflowEvent(BaseModel):
    event_type: Literal["workflow_started", "workflow_completed", "step_started", "step_completed"]
    workflow_id: str
    data: Dict[str, Any]
    timestamp: datetime
```

**RPC-вызовы** (через Celery tasks):

```python
# Вызов агента
@celery.task
def execute_agent(agent_id: str, context: Dict[str, Any]) -> Dict[str, Any]:
    pass

# Проверка гардрейла
@celery.task
def check_guardrail(guardrail_id: str, content: str) -> bool:
    pass
```

### 4.2 Внешнее API для интеграции с агентами и инструментами

**REST API (FastAPI)**:

| Метод | Путь                               | Описание                       |
| ----- | ---------------------------------- | ------------------------------ |
| POST  | `/api/v1/workflows`                | Создание и запуск workflow     |
| GET   | `/api/v1/workflows/{id}`           | Получение статуса workflow     |
| POST  | `/api/v1/workflows/{id}/pause`     | Приостановка workflow          |
| POST  | `/api/v1/workflows/{id}/resume`    | Возобновление workflow         |
| GET   | `/api/v1/workflows/{id}/artifacts` | Получение артефактов workflow  |
| GET   | `/api/v1/metrics/budget`           | Получение информации о бюджете |

**WebSocket API** для real-time уведомлений о состоянии workflow.

### 4.3 Webhook-и для внешних событий

**Конфигурация webhook-ов в AFL**:

```yaml
webhooks:
  - trigger: "git_push"
    url: "https://orchestrator.example.com/api/v1/webhooks/git"
    secret: "${WEBHOOK_SECRET}"

  - trigger: "jira_ticket_updated"
    url: "https://orchestrator.example.com/api/v1/webhooks/jira"
    secret: "${WEBHOOK_SECRET}"
```

**Обработчик webhook-ов**:

```python
@app.post("/api/v1/webhooks/{trigger}")
async def handle_webhook(
    trigger: str,
    payload: Dict[str, Any],
    signature: str = Header(None)
):
    # Верификация подписи
    # Поиск workflow, ожидающих этот триггер
    # Запуск соответствующих workflow
```

### 4.4 Форматы запросов/ответов (JSON схемы)

**Запуск workflow**:

```json
{
  "workflow_id": "code_review_workflow",
  "parameters": {
    "repository_url": "https://github.com/org/repo",
    "branch": "main"
  }
}
```

**Ответ**:

```json
{
  "execution_id": "uuid",
  "status": "pending",
  "estimated_time": 300,
  "webhook_url": "https://orchestrator.example.com/api/v1/executions/uuid/status"
}
```

**Получение статуса**:

```json
{
  "execution_id": "uuid",
  "status": "in_progress",
  "current_step": "analyze_code",
  "progress": 0.4,
  "artifacts": ["source_code"],
  "metrics": {
    "tokens_used": 2500,
    "time_elapsed": 120
  }
}
```

---

## 5. Компонентная Детализация (Component Specs)

### 5.1 Parser Module

**Ответственный**: Core Team **Срок MVP**: Неделя 1-2

#### 5.1.1 Поддерживаемый синтаксис

- Основной формат: YAML (с поддержкой anchors, aliases)
- Альтернативный формат: JSON (для программной генерации)
- Собственный DSL (будущее расширение)

#### 5.1.2 Валидация схемы конфига

Использование Pydantic для валидации:

```python
class AFLConfig(BaseModel):
    version: str = Field(pattern=r"^\d+\.\d+$")
    project: str
    budget: Optional[BudgetConfig]
    agents: List[AgentConfig]
    artifacts: List[ArtifactConfig]
    guardrails: List[GuardrailConfig]
    workflow: List[WorkflowStep]
```

#### 5.1.3 Обработка ошибок парсинга

- Детальные сообщения об ошибках с указанием строки и колонки
- Валидация ссылок (существует ли указанный agent/artifact/guardrail)
- Проверка циклов в графе зависимостей workflow

#### 5.1.4 Версионирование схемы AFL

- Мажорная версия в корне конфига (`version: "1.0"`)
- Автоматическая миграция конфигов между версиями
- Поддержка deprecated полей с предупреждениями

#### 5.1.5 Definition of Done (Parser Module)

| Критерий            | Метрика                                        | Метод проверки            |
| ------------------- | ---------------------------------------------- | ------------------------- |
| Валидация YAML/JSON | 100% корректных конфигов принимаются           | Интеграционные тесты      |
| Детализация ошибок  | Ошибка указывает строку/колонку с точностью ±1 | Ручная проверка 20 тестов |
| Валидация ссылок    | 100% битых ссылок детектируются                | Юнит-тесты                |
| Проверка циклов     | 100% циклических зависимостей детектируются    | Юнит-тесты                |
| Производительность  | Парсинг конфига ≤500 строк < 100 мс            | Бенчмарки                 |
| Покрытие тестами    | ≥90% кода покрыто тестами                      | pytest-cov                |
| Документация        | Все публичные методы задокументированы         | mypy --strict             |

---

### 5.2 Workflow Engine

**Ответственный**: Core Team **Срок MVP**: Неделя 2-4

#### 5.2.1 Машина состояний: состояния и переходы

```mermaid
stateDiagram-v2
    [*] --> PENDING
    PENDING --> RUNNING : start
    RUNNING --> PAUSED : pause
    PAUSED --> RUNNING : resume
    RUNNING --> COMPLETED : all_steps_done
    RUNNING --> FAILED : step_failed
    RUNNING --> CANCELLED : cancel
    PAUSED --> CANCELLED : cancel
    FAILED --> RUNNING : retry
    CANCELLED --> [*]
    COMPLETED --> [*]
```

#### 5.2.2 Обработка параллельных задач

- Параллельное выполнение независимых шагов
- Ограничение concurrency на уровне workflow
- Синхронизация через барьеры (wait for all)

#### 5.2.3 Обработка ошибок и retry-логика

- Exponential backoff для retry
- Максимальное количество попыток на шаг
- Кастомные обработчики ошибок (продолжить, пропустить шаг, завершить workflow)

#### 5.2.4 Приостановка и возобновление workflow

- Сериализация состояния в БД
- Возможность модификации параметров при возобновлении
- Сохранение промежуточных артефактов

#### 5.2.5 Definition of Done (Workflow Engine)

| Критерий                  | Метрика                       | Метод проверки       |
| ------------------------- | ----------------------------- | -------------------- |
| Машина состояний          | Все 7 состояний реализованы   | Юнит-тесты           |
| Переходы состояний        | 100% переходов корректны      | Интеграционные тесты |
| Параллельное выполнение   | ≥10 параллельных шагов        | Нагрузочные тесты    |
| Retry логика              | Exponential backoff работает  | Юнит-тесты           |
| Восстановление после сбоя | 100% workflow возобновляются  | Chaos-тесты          |
| Сериализация состояния    | Состояние сохраняется < 50 мс | Бенчмарки            |
| Покрытие тестами          | ≥85% кода покрыто тестами     | pytest-cov           |

---

### 5.3 Context Manager

**Ответственный**: AI Team **Срок MVP**: Неделя 3-5

#### 5.3.1 Стратегии сжатия контекста

1. **Summarization**: LLM-суммаризация предыдущего контекста
2. **Sliding Window**: Сохранение только последних N сообщений
3. **Key Information Extraction**: Извлечение ключевых фактов
4. **Hybrid**: Комбинация подходов в зависимости от типа контента

#### 5.3.2 Лимиты токенов на контекст

- Конфигурируемые лимиты на агента, шаг, workflow
- Динамическое сжатие при приближении к лимиту
- Предупреждения при усечении важного контекста

#### 5.3.3 Механизм передачи контекста между агентами

- Автоматическое включение релевантных артефактов
- Фильтрация конфиденциальной информации
- Аннотация источника каждого фрагмента контекста

#### 5.3.4 Хранение долгосрочной памяти агентов

- Векторная база данных (ChromaDB) для семантического поиска
- Индексирование ключевых решений и фактов
- Контекстуальный поиск при запросе агента

#### 5.3.5 Definition of Done (Context Manager)

| Критерий            | Метрика                            | Метод проверки        |
| ------------------- | ---------------------------------- | --------------------- |
| Сжатие контекста    | Потеря информации <10% (BLEU ≥0.9) | Валидация на датасете |
| Суммаризация        | 10K → 2K токенов за <5 сек         | Бенчмарки             |
| Sliding Window      | Сохранение последних N сообщений   | Юнит-тесты            |
| Извлечение фактов   | ≥90% ключевых фактов сохраняется   | Валидация качества    |
| Лимиты токенов      | Динамическое сжатие при 80% лимита | Интеграционные тесты  |
| Поиск в памяти      | Поиск <100 мс для 10K записей      | Бенчмарки             |
| Фильтрация секретов | 100% секретов удаляется            | Security-тесты        |
| Покрытие тестами    | ≥80% кода покрыто тестами          | pytest-cov            |

---

### 5.4 Guardrail Engine

**Ответственный**: Security Team **Срок MVP**: Неделя 4-6

#### 5.4.1 Архитектура Guardrail Engine

Guardrail Engine — это модуль проверки безопасности и качества выводов агентов.
Реализует паттерн **Chain of Responsibility**, где каждый гардрейл
последовательно проверяет контент. Поддерживает синхронные и асинхронные
проверки, кэширование результатов, и композицию правил.

**Ключевые компоненты**:

- **Guardrail Registry**: Реестр зарегистрированных гардрейлов
- **Validator Pipeline**: Цепочка проверок с ранним выходом при нарушении
- **Result Aggregator**: Агрегация результатов нескольких проверок
- **Action Executor**: Исполнитель действий при нарушении (block, modify, flag,
  rollback)

**Интерфейс гардрейла**:

```python
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from enum import Enum

class GuardrailAction(Enum):
    BLOCK = "block"
    MODIFY = "modify"
    FLAG = "flag"
    ROLLBACK = "rollback"

class GuardrailResult:
    def __init__(
        self,
        passed: bool,
        message: str = "",
        modified_content: Optional[str] = None,
        action: GuardrailAction = GuardrailAction.BLOCK,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.passed = passed
        self.message = message
        self.modified_content = modified_content
        self.action = action
        self.metadata = metadata or {}

class BaseGuardrail(ABC):
    """Базовый класс для всех гардрейлов"""

    def __init__(self, guardrail_id: str, config: Dict[str, Any]):
        self.guardrail_id = guardrail_id
        self.config = config

    @abstractmethod
    async def check(self, content: str, context: Dict[str, Any]) -> GuardrailResult:
        """Проверить контент на соответствие правилу"""
        pass

    @abstractmethod
    def get_description(self) -> str:
        """Описание гардрейла для логов и UI"""
        pass
```

#### 5.4.2 Реализация конкретных типов гардрейлов

##### Тип 1: Запрет определённых файлов и расширений

**Назначение**: Блокировка работы с опасными типами файлов (исполняемые файлы,
системные файлы, файлы с секретами).

**Реализация**:

```python
import re
from typing import Set, Pattern
from pathlib import Path

class FileExtensionGuardrail(BaseGuardrail):
    """Гардрейл для проверки расширений файлов"""

    def __init__(self, guardrail_id: str, config: Dict[str, Any]):
        super().__init__(guardrail_id, config)
        self.blocked_extensions: Set[str] = set(config.get("blocked_extensions", []))
        self.blocked_patterns: List[Pattern] = [
            re.compile(pattern) for pattern in config.get("blocked_patterns", [])
        ]
        self.allowed_paths: Set[str] = set(config.get("allowed_paths", []))
        self.action = GuardrailAction(config.get("action", "block"))

    async def check(self, content: str, context: Dict[str, Any]) -> GuardrailResult:
        """Проверить контент на наличие запрещённых файлов"""

        # Извлечение путей файлов из контента
        file_paths = self._extract_file_paths(content)
        violations = []

        for file_path in file_paths:
            # Проверка разрешённых путей (whitelist)
            if self._is_allowed_path(file_path):
                continue

            # Проверка расширения файла
            if self._has_blocked_extension(file_path):
                violations.append(f"Запрещённое расширение файла: {file_path}")

            # Проверка по регулярным выражениям
            if self._matches_blocked_pattern(file_path):
                violations.append(f"Файл соответствует запрещённому паттерну: {file_path}")

        if violations:
            return GuardrailResult(
                passed=False,
                message="Обнаружены запрещённые файлы:\n" + "\n".join(violations),
                action=self.action,
                metadata={"violations": violations, "file_paths": file_paths}
            )

        return GuardrailResult(passed=True, message="Проверка файлов пройдена")

    def _extract_file_paths(self, content: str) -> List[str]:
        """Извлечение путей файлов из текста"""
        # Паттерны для поиска путей файлов
        patterns = [
            r'[\'"]([/~\.][\w/\-\.]+\.\w{1,10})[\'"]',  # Кавычки
            r'`([/~\.][\w/\-\.]+\.\w{1,10})`',          # Бэктики
            r'path:\s*([\w/\-\.]+\.\w{1,10})',          # path: prefix
            r'File:\s*([\w/\-\.]+\.\w{1,10})',          # File: prefix
        ]

        file_paths = []
        for pattern in patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            file_paths.extend(matches)

        return list(set(file_paths))  # Удаление дубликатов

    def _has_blocked_extension(self, file_path: str) -> bool:
        """Проверка расширения файла"""
        path = Path(file_path.lower())
        extension = path.suffix.lower()
        return extension in self.blocked_extensions

    def _matches_blocked_pattern(self, file_path: str) -> bool:
        """Проверка по регулярным выражениям"""
        for pattern in self.blocked_patterns:
            if pattern.search(file_path):
                return True
        return False

    def _is_allowed_path(self, file_path: str) -> bool:
        """Проверка whitelist путей"""
        for allowed_path in self.allowed_paths:
            if file_path.startswith(allowed_path):
                return True
        return False

    def get_description(self) -> str:
        return f"FileExtensionGuardrail: Блокировка {len(self.blocked_extensions)} расширений файлов"

# Конфигурация в AFL
file_guardrail_config = """
guardrails:
  - id: "block_executables"
    type: "file_extension"
    blocked_extensions:
      - ".exe"
      - ".bat"
      - ".sh"
      - ".py"  # Можно блокировать скрипты
      - ".js"
      - ".php"
    blocked_patterns:
      - "^/etc/passwd$"
      - "^/proc/"
      - ".*secret.*\.(key|pem|env)$"
    allowed_paths:
      - "/tmp/"
      - "./allowed/"
    action: "block"
"""
```

##### Тип 2: Лимит токенов на шаг выполнения

**Назначение**: Контроль расхода токенов на уровне отдельного шага workflow.

**Реализация**:

```python
from datetime import datetime, timedelta
from typing import Optional
import asyncio

class TokenLimitGuardrail(BaseGuardrail):
    """Гардрейл для контроля лимита токенов"""

    def __init__(self, guardrail_id: str, config: Dict[str, Any]):
        super().__init__(guardrail_id, config)
        self.max_tokens: int = config["max_tokens"]
        self.warning_threshold: float = config.get("warning_threshold", 0.8)  # 80%
        self.reset_interval_seconds: Optional[int] = config.get("reset_interval")
        self.action = GuardrailAction(config.get("action", "block"))

        # Состояние (в продакшене хранится в Redis)
        self._token_count = 0
        self._last_reset = datetime.now()

    async def check(self, content: str, context: Dict[str, Any]) -> GuardrailResult:
        """Проверить, не превышен ли лимит токенов"""

        # Сброс счётчика по интервалу
        if self.reset_interval_seconds:
            self._reset_if_needed()

        # Получение количества токенов из контекста или оценка
        token_usage = context.get("token_usage", 0)
        if token_usage == 0:
            # Оценка токенов, если не предоставлено
            token_usage = self._estimate_tokens(content)

        new_total = self._token_count + token_usage

        # Проверка превышения лимита
        if new_total > self.max_tokens:
            return GuardrailResult(
                passed=False,
                message=f"Превышен лимит токенов: {new_total}/{self.max_tokens}",
                action=self.action,
                metadata={
                    "current_tokens": self._token_count,
                    "requested_tokens": token_usage,
                    "max_tokens": self.max_tokens,
                    "usage_percentage": (new_total / self.max_tokens) * 100
                }
            )

        # Проверка предупреждения (soft limit)
        warning_message = ""
        if new_total >= self.max_tokens * self.warning_threshold:
            warning_message = f"Внимание: использовано {new_total}/{self.max_tokens} токенов ({new_total/self.max_tokens*100:.1f}%)"

        # Обновление счётчика (в продакшене атомарно через Redis)
        self._token_count = new_total

        return GuardrailResult(
            passed=True,
            message=warning_message if warning_message else "Лимит токенов не превышен",
            metadata={
                "current_tokens": self._token_count,
                "max_tokens": self.max_tokens,
                "remaining_tokens": self.max_tokens - self._token_count,
                "warning_threshold": self.warning_threshold
            }
        )

    def _reset_if_needed(self):
        """Сбросить счётчик, если истёк интервал"""
        now = datetime.now()
        if now - self._last_reset > timedelta(seconds=self.reset_interval_seconds):
            self._token_count = 0
            self._last_reset = now

    def _estimate_tokens(self, text: str) -> int:
        """Оценка количества токенов в тексте (приблизительно)"""
        # В реальной реализации используем tiktoken или аналогичную библиотеку
        # Для примера: примерно 4 символа на токен
        return len(text) // 4

    def get_description(self) -> str:
        return f"TokenLimitGuardrail: Максимум {self.max_tokens} токенов"

# Конфигурация в AFL
token_guardrail_config = """
guardrails:
  - id: "step_token_limit"
    type: "token_limit"
    max_tokens: 10000
    warning_threshold: 0.8  # Предупреждение при 80%
    reset_interval: 3600    # Сброс каждый час
    action: "block"         # Блокировать при превышении
"""
```

##### Тип 3: Валидация вывода через LLM (LLM-as-a-Judge)

**Назначение**: Семантическая проверка вывода агента с использованием другой
LLM.

**Реализация**:

```python
import json
from typing import Tuple, List
import asyncio

class LLMJudgeGuardrail(BaseGuardrail):
    """Гардрейл с использованием LLM для проверки качества"""

    def __init__(self, guardrail_id: str, config: Dict[str, Any]):
        super().__init__(guardrail_id, config)
        self.validation_prompt: str = config["validation_prompt"]
        self.threshold: float = config.get("threshold", 0.7)
        self.model: str = config.get("model", "gpt-4")
        self.max_retries: int = config.get("max_retries", 3)
        self.action = GuardrailAction(config.get("action", "block"))

        # Кэш результатов (в продакшене - Redis)
        self._cache = {}

    async def check(self, content: str, context: Dict[str, Any]) -> GuardrailResult:
        """Проверить контент с помощью LLM"""

        # Проверка кэша
        cache_key = hash(content + self.validation_prompt)
        if cache_key in self._cache:
            return self._cache[cache_key]

        # Подготовка промпта для LLM-судьи
        judge_prompt = self._build_judge_prompt(content, context)

        # Вызов LLM с retry логикой
        llm_response = await self._call_llm_with_retry(judge_prompt)

        if not llm_response:
            return GuardrailResult(
                passed=False,
                message="Не удалось получить ответ от LLM-судьи",
                action=GuardrailAction.FLAG,  # Флагируем, но не блокируем
                metadata={"error": "LLM timeout"}
            )

        # Парсинг ответа LLM
        score, feedback, passed = self._parse_llm_response(llm_response)

        # Применение порога
        actually_passed = passed and score >= self.threshold

        result = GuardrailResult(
            passed=actually_passed,
            message=feedback,
            metadata={
                "score": score,
                "threshold": self.threshold,
                "model": self.model,
                "feedback": feedback
            },
            action=self.action if not actually_passed else GuardrailAction.FLAG
        )

        # Сохранение в кэш
        self._cache[cache_key] = result

        return result

    def _build_judge_prompt(self, content: str, context: Dict[str, Any]) -> List[Dict[str, str]]:
        """Построить промпт для LLM-судьи"""

        system_prompt = f"""Ты — эксперт, оценивающий качество вывода AI-агента.

Критерии оценки:
1. Соответствие заданию: {context.get('task_description', 'Не указано')}
2. Полнота ответа
3. Точность информации
4. Структура и ясность
5. Отсутствие вредоносного контента

Оцени вывод по шкале от 0.0 до 1.0.
Верни ответ в формате JSON:
{{
    "score": 0.95,
    "feedback": "Конструктивная обратная связь...",
    "passed": true
}}"""

        user_prompt = f"""{self.validation_prompt}

Вывод агента для проверки:
```

{content}

```

Оцени вывод и верни JSON ответ."""

        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

    async def _call_llm_with_retry(self, messages: List[Dict[str, str]]) -> Optional[str]:
        """Вызов LLM с механизмом повторных попыток"""

        for attempt in range(self.max_retries):
            try:
                # В реальной реализации используем абстракцию LLMProvider
                # from orchestrator.integrations.llm import get_llm_provider
                # llm = get_llm_provider(self.model)
                # response = await llm.chat_completion(messages, temperature=0.1)
                # return response.choices[0].message.content

                # Заглушка для примера
                await asyncio.sleep(0.1)
                return json.dumps({
                    "score": 0.85,
                    "feedback": "Вывод соответствует требованиям, но можно улучшить структуру.",
                    "passed": True
                })

            except Exception as e:
                if attempt == self.max_retries - 1:
                    return None
                await asyncio.sleep(2 ** attempt)  # Exponential backoff

        return None

    def _parse_llm_response(self, response: str) -> Tuple[float, str, bool]:
        """Парсинг ответа LLM"""
        try:
            data = json.loads(response)
            score = float(data.get("score", 0))
            feedback = data.get("feedback", "Нет обратной связи")
            passed = bool(data.get("passed", False))
            return score, feedback, passed
        except (json.JSONDecodeError, ValueError) as e:
            # Fallback: пытаемся извлечь оценку из текста
            import re
            score_match = re.search(r'(\d+\.\d+|\d+)', response)
            score = float(score_match.group(1)) / 100 if score_match else 0.5

            return score, f"Ошибка парсинга: {str(e)}. Ответ LLM: {response}", score >= 0.5

    def get_description(self) -> str:
        return f"LLMJudgeGuardrail: Проверка через {self.model} с порогом {self.threshold}"

# Конфигурация в AFL
llm_judge_config = """
guardrails:
  - id: "code_quality_check"
    type: "llm_judge"
    validation_prompt: |
      Оцени качество кода по критериям:
      1. Читаемость и стиль
      2. Отсутствие уязвимостей
      3. Эффективность алгоритмов
      4. Качество комментариев
    threshold: 0.7
    model: "gpt-4"
    max_retries: 3
    action: "block"
"""
```

#### 5.4.3 Система регистрации и выполнения гардрейлов

```python
class GuardrailEngine:
    """Движок выполнения гардрейлов"""

    def __init__(self):
        self._registry: Dict[str, Type[BaseGuardrail]] = {}
        self._register_builtin_guardrails()

    def register_guardrail(self, guardrail_type: str, guardrail_class: Type[BaseGuardrail]):
        """Регистрация нового типа гардрейла"""
        self._registry[guardrail_type] = guardrail_class

    async def execute_guardrails(
        self,
        content: str,
        guardrail_configs: List[Dict[str, Any]],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Выполнить цепочку гардрейлов"""

        results = []
        final_content = content
        should_block = False
        violations = []

        for config in guardrail_configs:
            guardrail_id = config["id"]
            guardrail_type = config["type"]

            if guardrail_type not in self._registry:
                raise ValueError(f"Неизвестный тип гардрейла: {guardrail_type}")

            # Создание экземпляра гардрейла
            guardrail_class = self._registry[guardrail_type]
            guardrail = guardrail_class(guardrail_id, config)

            # Выполнение проверки
            result = await guardrail.check(final_content, context)
            results.append({
                "guardrail_id": guardrail_id,
                "guardrail_type": guardrail_type,
                "result": result
            })

            # Применение модификаций к контенту
            if result.modified_content is not None:
                final_content = result.modified_content

            # Обработка действий
            if not result.passed:
                violations.append({
                    "guardrail_id": guardrail_id,
                    "message": result.message,
                    "action": result.action.value
                })

                if result.action == GuardrailAction.BLOCK:
                    should_block = True
                    break  # Прерываем цепочку при блокировке
                elif result.action == GuardrailAction.ROLLBACK:
                    # Откат к предыдущему состоянию workflow
                    context["rollback_requested"] = True

        return {
            "passed": not should_block and len(violations) == 0,
            "final_content": final_content,
            "results": results,
            "violations": violations,
            "should_block": should_block,
            "context": context
        }

    def _register_builtin_guardrails(self):
        """Регистрация встроенных гардрейлов"""
        self.register_guardrail("file_extension", FileExtensionGuardrail)
        self.register_guardrail("token_limit", TokenLimitGuardrail)
        self.register_guardrail("llm_judge", LLMJudgeGuardrail)
        self.register_guardrail("regex", RegexGuardrail)  # Предполагаем существование
```

#### 5.4.4 Конфигурация гардрейлов в AFL

```yaml
# Полный пример конфигурации с тремя типами гардрейлов
guardrails:
  # 1. Запрет файлов
  - id: "security_files"
    type: "file_extension"
    blocked_extensions:
      - ".exe"
      - ".bat"
      - ".sh"
      - ".dll"
      - ".so"
    blocked_patterns:
      - ".*\.(key|pem|env|secret)$"
      - "^/etc/"
      - "^/proc/"
    action: "block"

  # 2. Лимит токенов
  - id: "step_budget"
    type: "token_limit"
    max_tokens: 5000
    warning_threshold: 0.75
    reset_interval: 1800  # 30 минут
    action: "flag"  # Только предупреждение

  # 3. LLM-валидация
  - id: "quality_check"
    type: "llm_judge"
    validation_prompt: |
      Проверь, что вывод:
      1. Отвечает на поставленный вопрос
      2. Не содержит вредоносных инструкций
      3. Корректен с технической точки зрения
      4. Не содержит PII данных
    threshold: 0.6
    model: "gpt-3.5-turbo"
    action: "modify"  # Попробовать исправить

  # 4. Кастомный гардрейл (Python функция)
  - id: "custom_check"
    type: "python_function"
    module: "custom_guardrails.security"
    function: "check_malicious_code"
    parameters:
      severity_level: "high"
    action: "block"
```

#### 5.4.5 Обработка нарушений и компенсирующие действия

```python
class GuardrailViolationHandler:
    """Обработчик нарушений гардрейлов"""

    async def handle_violation(
        self,
        violation_result: Dict[str, Any],
        workflow_execution_id: str,
        step_id: str
    ) -> Dict[str, Any]:
        """Обработать нарушение гардрейла"""

        action = violation_result.get("action", "block")

        handlers = {
            "block": self._handle_block,
            "modify": self._handle_modify,
            "flag": self._handle_flag,
            "rollback": self._handle_rollback
        }

        handler = handlers.get(action)
        if handler:
            return await handler(violation_result, workflow_execution_id, step_id)

        # По умолчанию блокируем
        return await self._handle_block(violation_result, workflow_execution_id, step_id)

    async def _handle_block(
        self,
        violation_result: Dict[str, Any],
        workflow_execution_id: str,
        step_id: str
    ) -> Dict[str, Any]:
        """Обработка блокировки"""

        # Сохранение нарушения в БД
        await self._save_violation_to_db(
            workflow_execution_id,
            step_id,
            violation_result
        )

        # Уведомление через webhook
        await self._send_webhook_notification(
            "guardrail_blocked",
            {
                "workflow_execution_id": workflow_execution_id,
                "step_id": step_id,
                "violation": violation_result
            }
        )

        return {
            "action": "block",
            "message": "Workflow заблокирован из-за нарушения гардрейла",
            "can_continue": False,
            "requires_human_intervention": True
        }

    async def _handle_modify(
        self,
        violation_result: Dict[str, Any],
        workflow_execution_id: str,
        step_id: str
    ) -> Dict[str, Any]:
        """Обработка с модификацией контента"""

        modified_content = violation_result.get("modified_content")

        if modified_content:
            # Логирование модификации
            await self._log_modification(
                workflow_execution_id,
                step_id,
                violation_result,
                modified_content
            )

            return {
                "action": "modify",
                "message": "Контент был автоматически исправлен",
                "modified_content": modified_content,
                "can_continue": True,
                "requires_human_intervention": False
            }

        # Если модификация не удалась, блокируем
        return await self._handle_block(violation_result, workflow_execution_id, step_id)
```

#### 5.4.6 Тестирование гардрейлов

```python
import pytest
from unittest.mock import AsyncMock, Mock

@pytest.mark.asyncio
async def test_file_extension_guardrail():
    """Тест гардрейла проверки расширений файлов"""

    config = {
        "blocked_extensions": [".exe", ".bat"],
        "action": "block"
    }

    guardrail = FileExtensionGuardrail("test_guardrail", config)

    # Тест с запрещённым файлом
    content = "Скачать программу: setup.exe"
    result = await guardrail.check(content, {})

    assert result.passed == False
    assert ".exe" in result.message

    # Тест с разрешённым файлом
    content = "Документ: report.pdf"
    result = await guardrail.check(content, {})

    assert result.passed == True

@pytest.mark.asyncio
async def test_token_limit_guardrail():
    """Тест гардрейла лимита токенов"""

    config = {
        "max_tokens": 100,
        "warning_threshold": 0.8
    }

    guardrail = TokenLimitGuardrail("token_guardrail", config)

    # Первый вызов - 50 токенов
    context = {"token_usage": 50}
    result = await guardrail.check("", context)
    assert result.passed == True

    # Второй вызов - 60 токенов (превышение)
    context = {"token_usage": 60}
    result = await guardrail.check("", context)
    assert result.passed == False
    assert "Превышен лимит" in result.message

@pytest.mark.asyncio
async def test_llm_judge_guardrail():
    """Тест LLM-судьи (с моком)"""

    config = {
        "validation_prompt": "Оцени качество",
        "threshold": 0.7,
        "model": "gpt-4"
    }

    guardrail = LLMJudgeGuardrail("llm_judge", config)

    # Мок вызова LLM
    guardrail._call_llm_with_retry = AsyncMock(
        return_value='{"score": 0.9, "feedback": "Хорошо", "passed": true}'
    )

    result = await guardrail.check("Пример контента", {})

    assert result.passed == True
    assert result.metadata["score"] == 0.9
```

#### 5.4.7 Definition of Done (Guardrail Engine)

| Критерий                | Метрика                         | Метод проверки        |
| ----------------------- | ------------------------------- | --------------------- |
| Типы гардрейлов         | ≥3 типов реализовано            | Интеграционные тесты  |
| False positive rate     | <5% на 1000 примеров            | Валидация на датасете |
| False negative rate     | <1% на 1000 примеров            | Валидация на датасете |
| Производительность      | Проверка <100 мс (p95)          | Бенчмарки             |
| Chain of Responsibility | Последовательная проверка       | Юнит-тесты            |
| Действия при нарушении  | block/modify/flag/rollback      | Интеграционные тесты  |
| Кэширование результатов | hit rate ≥50% для повторяющихся | Мониторинг            |
| Покрытие тестами        | ≥90% кода покрыто тестами       | pytest-cov            |

---

### 5.5 Budget Tracker

**Ответственный**: Core Team **Срок MVP**: Неделя 2-3

#### 5.5.1 Учёт токенов по провайдерам и моделям

- Интеграция с провайдерами: получение точного расчёта токенов
- Кэширование цен для офлайн-расчётов
- Поддержка разных валют и курсов конвертации

#### 5.5.2 Лимиты на агент/задачу/проект

- Иерархические лимиты: проект → workflow → шаг → агент
- Soft limits (предупреждение) vs hard limits (блокировка)
- Динамическое перераспределение бюджета между workflow

#### 5.5.3 Уведомления о приближении к лимиту

- Email/Slack уведомления
- Webhook-и для интеграции с системами мониторинга
- Прогнозирование расхода на основе истории

#### 5.5.4 Отчётность и логи затрат

- Ежедневные/еженедельные отчёты
- Детализация по моделям и провайдерам
- Визуализация трендов (Grafana dashboards)

#### 5.5.5 Definition of Done (Budget Tracker)

| Критерий             | Метрика                               | Метод проверки       |
| -------------------- | ------------------------------------- | -------------------- |
| Учёт токенов         | Точность ±5% vs провайдер             | Сверка с OpenAI API  |
| Иерархические лимиты | 4 уровня (проект/workflow/step/agent) | Интеграционные тесты |
| Soft limits          | Уведомление при 80%                   | Юнит-тесты           |
| Hard limits          | Блокировка 100% при превышении        | Интеграционные тесты |
| Уведомления          | Email/Slack/Webhook за <1 сек         | Интеграционные тесты |
| Прогнозирование      | Точность прогноза ≥80%                | Валидация на истории |
| Отчётность           | Grafana дашборды готовы               | Ручная проверка      |
| Покрытие тестами     | ≥85% кода покрыто тестами             | pytest-cov           |

---

### 5.6 Agent Executor

**Ответственный**: AI Team **Срок MVP**: Неделя 1-3

#### 5.6.1 Протокол взаимодействия с LLM-агентами

```python
class IAgent(Protocol):
    async def execute(
        self,
        context: Dict[str, Any],
        tools: List[ITool]
    ) -> Dict[str, Any]:
        """Выполнить задачу агента"""
        pass
```

#### 5.6.2 Управление инструментами (tools)

- Регистрация инструментов через декораторы
- Автоматическое описание инструментов для LLM
- Ограничение доступа инструментов по политикам безопасности

#### 5.6.3 Таймауты и обработка зависаний

- Конфигурируемые таймауты на выполнение агента
- Circuit breaker паттерн для нестабильных провайдеров
- Fallback-стратегии (использование другой модели)

#### 5.6.4 Логирование действий агента

- Полный лог промптов и ответов
- Запись использованных инструментов с параметрами
- Аудиторский след для compliance

#### 5.6.5 Definition of Done (Agent Executor)

| Критерий                 | Метрика                       | Метод проверки       |
| ------------------------ | ----------------------------- | -------------------- |
| IAgent интерфейс         | Все методы реализованы        | Ревью кода           |
| Управление инструментами | ≥5 инструментов доступно      | Интеграционные тесты |
| Таймауты                 | Конфигурируемые, работают     | Юнит-тесты           |
| Circuit breaker          | Срабатывает при 5 ошибках     | Интеграционные тесты |
| Fallback стратегии       | Переключение на другую модель | Интеграционные тесты |
| Логирование              | 100% действий в логах         | Аудит логов          |
| Время запуска агента     | <1 сек (p95)                  | Бенчмарки            |
| Покрытие тестами         | ≥85% кода покрыто тестами     | pytest-cov           |

---

## 6. Интеграции (Integrations)

### 6.1 LLM-провайдеры

#### Библиотеки Python и подходы

| Провайдер         | Основные библиотеки                                 | Альтернативы                      |
| ----------------- | --------------------------------------------------- | --------------------------------- |
| **OpenAI**        | `openai` (официальная), `litellm` (универсальная)   | `aiohttp` для прямых запросов     |
| **Anthropic**     | `anthropic` (официальная), `litellm`                | `anthropic[vertex]` для Vertex AI |
| **Local модели**  | `llama-cpp-python`, `transformers`, `vllm`          | `ollama` Python client            |
| **Azure OpenAI**  | `openai` (с параметрами endpoint), `azure-identity` | Прямые REST запросы               |
| **Универсальные** | `litellm` (рекомендуется для абстракции)            | `langchain` (тяжеловесный)        |

**Рекомендация для MVP**: Использовать `litellm` как единую абстракцию над всеми
провайдерами.

#### Конкретная реализация с обработкой ошибок

```python
import asyncio
import logging
from typing import List, Dict, Any, Optional
from enum import Enum
from dataclasses import dataclass
from datetime import datetime
import backoff
import litellm
from litellm import acompletion
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

class LLMProvider(Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    AZURE_OPENAI = "azure_openai"
    OLLAMA = "ollama"
    VLLM = "vllm"

@dataclass
class LLMResponse:
    content: str
    token_usage: Dict[str, int]
    model: str
    finish_reason: str
    response_time: float

class LLMIntegrationManager:
    """Менеджер интеграций с LLM провайдерами"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self._setup_litellm()
        self.circuit_breaker_state = {}  # Состояние circuit breaker по моделям
        self.fallback_models = config.get("fallback_models", {
            "gpt-4": "gpt-3.5-turbo",
            "claude-3-opus": "claude-3-sonnet"
        })

    def _setup_litellm(self):
        """Настройка litellm с конфигурацией провайдеров"""

        # Конфигурация API ключей
        litellm.api_key = self.config.get("api_keys", {})

        # Настройка таймаутов и ретраев
        litellm.set_verbose = self.config.get("debug", False)
        litellm.drop_params = True  # Игнорировать неподдерживаемые параметры

        # Кэширование (опционально)
        if self.config.get("enable_caching", False):
            import diskcache
            cache = diskcache.Cache("llm_cache")
            litellm.cache = cache

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry_error_callback=lambda retry_state: None
    )
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: str,
        **kwargs
    ) -> Optional[LLMResponse]:
        """Вызов LLM с обработкой ошибок и retry логикой"""

        # Проверка circuit breaker
        if self._is_circuit_open(model):
            logger.warning(f"Circuit открыт для модели {model}, используем fallback")
            fallback_model = self.fallback_models.get(model)
            if fallback_model and fallback_model != model:
                return await self.chat_completion(messages, fallback_model, **kwargs)
            return None

        start_time = datetime.now()

        try:
            # Подготовка параметров
            completion_params = {
                "model": model,
                "messages": messages,
                "temperature": kwargs.get("temperature", 0.1),
                "max_tokens": kwargs.get("max_tokens", 2000),
                "timeout": kwargs.get("timeout", 30.0),
            }

            # Добавляем специфичные параметры провайдера
            if model.startswith("gpt-"):
                completion_params["presence_penalty"] = kwargs.get("presence_penalty", 0.0)
            elif "claude" in model:
                completion_params["max_tokens_to_sample"] = completion_params.pop("max_tokens")

            # Асинхронный вызов через litellm
            response = await acompletion(**completion_params)

            # Обработка успешного ответа
            response_time = (datetime.now() - start_time).total_seconds()

            # Сброс circuit breaker при успехе
            self._record_success(model)

            return LLMResponse(
                content=response.choices[0].message.content,
                token_usage=response.usage.dict() if hasattr(response, 'usage') else {},
                model=model,
                finish_reason=response.choices[0].finish_reason,
                response_time=response_time
            )

        except Exception as e:
            response_time = (datetime.now() - start_time).total_seconds()
            await self._handle_llm_error(e, model, response_time, messages, **kwargs)
            return None

    async def _handle_llm_error(
        self,
        error: Exception,
        model: str,
        response_time: float,
        messages: List[Dict[str, str]],
        **kwargs
    ) -> None:
        """Обработка ошибок LLM"""

        error_type = type(error).__name__

        # Классификация ошибок
        if "timeout" in str(error).lower() or response_time > 30:
            logger.warning(f"Таймаут модели {model}: {error}")
            self._record_failure(model, "timeout")

        elif "rate limit" in str(error).lower():
            logger.warning(f"Rate limit для модели {model}: {error}")
            self._record_failure(model, "rate_limit")
            # Exponential backoff для rate limits
            await asyncio.sleep(5)

        elif "authentication" in str(error).lower() or "401" in str(error):
            logger.error(f"Ошибка аутентификации для {model}: {error}")
            self._record_failure(model, "auth_error")
            # Критическая ошибка - не retry

        elif "context length" in str(error).lower():
            logger.error(f"Превышен контекст для {model}: {error}")
            # Не retry - нужно уменьшить контекст
            raise error

        else:
            logger.error(f"Неизвестная ошибка LLM {model}: {error}")
            self._record_failure(model, "unknown")

    def _is_circuit_open(self, model: str) -> bool:
        """Проверка состояния circuit breaker"""
        state = self.circuit_breaker_state.get(model, {})
        failures = state.get("failures", 0)
        last_failure = state.get("last_failure")

        # Если больше 5 ошибок за последние 2 минуты
        if failures >= 5 and last_failure:
            time_since_failure = (datetime.now() - last_failure).total_seconds()
            if time_since_failure < 120:  # 2 минуты
                return True

        return False

    def _record_success(self, model: str):
        """Запись успешного вызова"""
        if model not in self.circuit_breaker_state:
            self.circuit_breaker_state[model] = {"successes": 0, "failures": 0}
        self.circuit_breaker_state[model]["successes"] += 1
        self.circuit_breaker_state[model]["failures"] = 0

    def _record_failure(self, model: str, error_type: str):
        """Запись неудачного вызова"""
        if model not in self.circuit_breaker_state:
            self.circuit_breaker_state[model] = {"successes": 0, "failures": 0}
        self.circuit_breaker_state[model]["failures"] += 1
        self.circuit_breaker_state[model]["last_failure"] = datetime.now()
        self.circuit_breaker_state[model]["last_error_type"] = error_type

    async def count_tokens(self, text: str, model: str) -> int:
        """Подсчёт токенов (универсальный через tiktoken)"""
        try:
            import tiktoken

            # Маппинг моделей на энкодинги
            encoding_map = {
                "gpt-4": "cl100k_base",
                "gpt-3.5-turbo": "cl100k_base",
                "text-davinci-003": "p50k_base",
                "code-davinci-002": "p50k_base",
            }

            encoding_name = encoding_map.get(model, "cl100k_base")
            encoding = tiktoken.get_encoding(encoding_name)

            return len(encoding.encode(text))

        except ImportError:
            # Fallback: приблизительный подсчёт (4 символа ≈ 1 токен)
            return len(text) // 4
        except Exception as e:
            logger.error(f"Ошибка подсчёта токенов: {e}")
            return len(text) // 4  # Консервативная оценка

# Пример конфигурации
llm_config = {
    "api_keys": {
        "openai": "sk-...",
        "anthropic": "sk-ant-...",
        "azure_openai": {
            "api_key": "...",
            "api_base": "https://{resource}.openai.azure.com/",
            "api_version": "2024-02-15-preview"
        }
    },
    "fallback_models": {
        "gpt-4": "gpt-3.5-turbo-16k",
        "claude-3-opus": "claude-3-sonnet-20240229"
    },
    "enable_caching": True,
    "debug": False,
    "default_timeout": 30.0,
    "max_retries": 3
}

# Пример использования
async def example_llm_usage():
    manager = LLMIntegrationManager(llm_config)

    messages = [
        {"role": "system", "content": "Ты - помощник по коду."},
        {"role": "user", "content": "Объясни паттерн Singleton."}
    ]

    try:
        response = await manager.chat_completion(
            messages=messages,
            model="gpt-4",
            temperature=0.1,
            max_tokens=500
        )

        if response:
            print(f"Ответ: {response.content}")
            print(f"Токены: {response.token_usage}")
            print(f"Время: {response.response_time:.2f} сек")
        else:
            print("Не удалось получить ответ от LLM")

    except Exception as e:
        print(f"Критическая ошибка: {e}")
```

#### Обработка специфичных ошибок по провайдерам

```python
class ProviderSpecificErrorHandler:
    """Обработчик специфичных ошибок провайдеров"""

    @staticmethod
    async def handle_openai_error(error: Exception, attempt: int) -> bool:
        """Обработка ошибок OpenAI"""
        error_str = str(error).lower()

        if "insufficient_quota" in error_str:
            logger.error("Недостаточно квоты в OpenAI аккаунте")
            return False  # Не retry

        elif "billing_not_active" in error_str:
            logger.error("Биллинг не активирован для OpenAI")
            return False

        elif "invalid_api_key" in error_str:
            logger.error("Неверный API ключ OpenAI")
            return False

        elif "model_not_found" in error_str:
            logger.error(f"Модель не найдена: {error}")
            return False

        # Для остальных ошибок - retry
        return True

    @staticmethod
    async def handle_anthropic_error(error: Exception, attempt: int) -> bool:
        """Обработка ошибок Anthropic"""
        error_str = str(error).lower()

        if "invalid_api_key" in error_str:
            logger.error("Неверный API ключ Anthropic")
            return False

        elif "payment_required" in error_str:
            logger.error("Требуется оплата для Anthropic")
            return False

        elif "overloaded" in error_str:
            # Перегрузка сервиса - ждём подольше
            wait_time = min(2 ** attempt, 30)
            logger.warning(f"Anthropic перегружен, ждём {wait_time} сек")
            await asyncio.sleep(wait_time)
            return True

        return True
```

### 6.2 Системы контроля версий (Git)

#### Библиотеки Python

| Задача                         | Основная библиотека           | Альтернативы                         |
| ------------------------------ | ----------------------------- | ------------------------------------ |
| **Основные операции**          | `gitpython` (рекомендуется)   | `pygit2` (более быстрая, но сложнее) |
| **Низкоуровневые операции**    | `dulwich` (чистый Python)     | `subprocess` (прямой вызов git)      |
| **Работа с GitHub/GitLab API** | `github` (PyGithub), `gitlab` | `aiohttp` для REST API               |
| **Асинхронные операции**       | `aiogit` (экспериментальная)  | `asyncio.subprocess`                 |

#### Конкретная реализация с обработкой ошибок

```python
import os
import tempfile
import shutil
import asyncio
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from enum import Enum
import git
from git import Repo, GitCommandError
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

logger = logging.getLogger(__name__)

class GitOperation(Enum):
    CLONE = "clone"
    PULL = "pull"
    CHECKOUT = "checkout"
    FETCH = "fetch"
    DIFF = "diff"
    LOG = "log"

@dataclass
class GitRepository:
    local_path: Path
    repo_url: str
    branch: str
    repo: Optional[Repo] = None

class GitIntegrationManager:
    """Менеджер интеграций с Git"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.temp_dir = Path(config.get("temp_dir", tempfile.gettempdir())) / "afl_git"
        self.temp_dir.mkdir(parents=True, exist_ok=True)

        # Настройка Git (глобальная конфигурация)
        self.git_user = config.get("git_user", {"name": "AFL Orchestrator", "email": "orchestrator@example.com"})
        self.ssh_key_path = config.get("ssh_key_path")
        self.credentials = config.get("credentials", {})  # Для HTTPS

        # Кэш репозиториев
        self.repo_cache: Dict[str, GitRepository] = {}

    async def clone_repository(
        self,
        repo_url: str,
        branch: str = "main",
        depth: Optional[int] = None,
        clean: bool = True
    ) -> Optional[GitRepository]:
        """Клонирование репозитория с обработкой ошибок"""

        # Создание уникального пути для клона
        repo_name = self._extract_repo_name(repo_url)
        local_path = self.temp_dir / repo_name

        # Очистка предыдущего клона если требуется
        if clean and local_path.exists():
            await self._safe_remove_directory(local_path)

        try:
            # Подготовка опций клонирования
            clone_options = {
                "url": repo_url,
                "to_path": str(local_path),
                "branch": branch,
            }

            # Добавление depth для shallow clone
            if depth:
                clone_options["depth"] = depth

            # Настройка аутентификации
            self._configure_auth(repo_url)

            # Асинхронное клонирование через ThreadPoolExecutor
            loop = asyncio.get_event_loop()
            repo = await loop.run_in_executor(
                None,
                lambda: self._clone_with_retry(**clone_options)
            )

            # Настройка пользователя Git
            with repo.config_writer() as config:
                config.set_value("user", "name", self.git_user["name"])
                config.set_value("user", "email", self.git_user["email"])

            git_repo = GitRepository(
                local_path=local_path,
                repo_url=repo_url,
                branch=branch,
                repo=repo
            )

            self.repo_cache[repo_url] = git_repo
            logger.info(f"Успешно клонирован {repo_url} в {local_path}")
            return git_repo

        except Exception as e:
            await self._handle_git_error(e, GitOperation.CLONE, {
                "repo_url": repo_url,
                "branch": branch,
                "local_path": str(local_path)
            })
            return None

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((GitCommandError, TimeoutError))
    )
    def _clone_with_retry(self, **kwargs) -> Repo:
        """Клонирование с повторными попытками"""
        try:
            return Repo.clone_from(**kwargs)
        except GitCommandError as e:
            # Анализ конкретной ошибки
            error_msg = str(e).lower()

            if "authentication" in error_msg or "403" in str(e):
                raise PermissionError(f"Ошибка аутентификации Git: {e}")
            elif "not found" in error_msg:
                raise FileNotFoundError(f"Репозиторий не найден: {e}")
            elif "timeout" in error_msg:
                raise TimeoutError(f"Таймаут при клонировании: {e}")
            else:
                raise

    async def get_file_content(
        self,
        repo: GitRepository,
        file_path: str,
        commit_hash: Optional[str] = None
    ) -> Optional[str]:
        """Получение содержимого файла из репозитория"""

        try:
            full_path = repo.local_path / file_path

            if commit_hash:
                # Получение файла из конкретного коммита
                loop = asyncio.get_event_loop()
                content = await loop.run_in_executor(
                    None,
                    lambda: repo.repo.git.show(f"{commit_hash}:{file_path}")
                )
                return content
            else:
                # Чтение из рабочей директории
                if full_path.exists():
                    return full_path.read_text(encoding="utf-8")
                else:
                    logger.warning(f"Файл не найден: {file_path}")
                    return None

        except Exception as e:
            await self._handle_git_error(e, GitOperation.CLONE, {
                "repo_url": repo.repo_url,
                "file_path": file_path,
                "commit_hash": commit_hash
            })
            return None

    async def get_diff(
        self,
        repo: GitRepository,
        base_ref: str = "HEAD~1",
        target_ref: str = "HEAD"
    ) -> List[Dict[str, Any]]:
        """Получение diff между коммитами"""

        try:
            loop = asyncio.get_event_loop()
            diff_output = await loop.run_in_executor(
                None,
                lambda: repo.repo.git.diff(f"{base_ref}..{target_ref}", "--name-status")
            )

            # Парсинг diff
            changes = []
            for line in diff_output.strip().split("\n"):
                if line:
                    status, path = line.split("\t", 1)
                    changes.append({
                        "status": status,  # A (added), M (modified), D (deleted)
                        "path": path,
                        "full_path": str(repo.local_path / path)
                    })

            return changes

        except Exception as e:
            await self._handle_git_error(e, GitOperation.DIFF, {
                "repo_url": repo.repo_url,
                "base_ref": base_ref,
                "target_ref": target_ref
            })
            return []

    async def commit_and_push(
        self,
        repo: GitRepository,
        file_paths: List[str],
        commit_message: str,
        branch: Optional[str] = None
    ) -> bool:
        """Коммит и push изменений"""

        try:
            # Переключение на нужную ветку если указана
            if branch and branch != repo.branch:
                await self._checkout_branch(repo, branch)

            # Добавление файлов
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: repo.repo.index.add(file_paths)
            )

            # Создание коммита
            await loop.run_in_executor(
                None,
                lambda: repo.repo.index.commit(commit_message)
            )

            # Push в remote
            await loop.run_in_executor(
                None,
                lambda: repo.repo.remote().push()
            )

            logger.info(f"Успешно закоммичено и запушено: {commit_message}")
            return True

        except Exception as e:
            await self._handle_git_error(e, GitOperation.CLONE, {
                "repo_url": repo.repo_url,
                "file_paths": file_paths,
                "commit_message": commit_message
            })
            return False

    def _configure_auth(self, repo_url: str):
        """Настройка аутентификации Git"""

        if repo_url.startswith("git@"):
            # SSH аутентификация
            if self.ssh_key_path:
                os.environ["GIT_SSH_COMMAND"] = f"ssh -i {self.ssh_key_path} -o StrictHostKeyChecking=no"

        elif "https://" in repo_url:
            # HTTPS аутентификация
            if "github.com" in repo_url and "github_token" in self.credentials:
                # Для GitHub можно использовать токен
                import base64
                token = self.credentials["github_token"]
                auth_url = repo_url.replace("https://", f"https://{token}@")
                # Обновляем URL для клонирования
                # (нужно передать в параметры клонирования)

    async def _handle_git_error(
        self,
        error: Exception,
        operation: GitOperation,
        context: Dict[str, Any]
    ) -> None:
        """Обработка ошибок Git"""

        error_type = type(error).__name__
        error_msg = str(error).lower()

        logger.error(f"Git ошибка при {operation.value}: {error} | Контекст: {context}")

        # Классификация ошибок для мониторинга
        if "authentication" in error_msg or "permission" in error_msg:
            logger.error("Ошибка аутентификации Git. Проверьте SSH ключи или токены.")

        elif "not found" in error_msg or "404" in str(error):
            logger.error(f"Репозиторий или путь не найден: {context.get('repo_url')}")

        elif "timeout" in error_msg or "timed out" in error_msg:
            logger.warning(f"Таймаут при операции {operation.value}")

        elif "conflict" in error_msg:
            logger.error("Конфликт слияния. Требуется ручное разрешение.")

        elif "dirty" in error_msg:
            logger.warning("Рабочая директория не чистая. Используйте clean=True")

        elif "shallow" in error_msg and operation == GitOperation.PULL:
            logger.error("Shallow clone не поддерживает pull. Используйте depth=None")

        # Метрики для мониторинга
        self._record_git_metric(operation, "failure", context)

    async def _safe_remove_directory(self, path: Path) -> None:
        """Безопасное удаление директории"""
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, lambda: shutil.rmtree(path, ignore_errors=True))
        except Exception as e:
            logger.warning(f"Ошибка при удалении директории {path}: {e}")

    def _extract_repo_name(self, repo_url: str) -> str:
        """Извлечение имени репозитория из URL"""
        # Извлечение имени из git@github.com:user/repo.git
        if ":" in repo_url and "@" in repo_url:
            return repo_url.split(":")[1].replace(".git", "")
        # Извлечение из https://github.com/user/repo.git
        elif "/" in repo_url:
            parts = repo_url.rstrip("/").split("/")
            name = parts[-1].replace(".git", "")
            return name
        return repo_url.replace("/", "_").replace(":", "_")

    def _record_git_metric(self, operation: GitOperation, status: str, context: Dict[str, Any]):
        """Запись метрик Git операций (для мониторинга)"""
        # В реальной реализации отправляем в Prometheus/StatsD
        metric_data = {
            "operation": operation.value,
            "status": status,
            "repo": context.get("repo_url", "unknown"),
            "timestamp": datetime.now().isoformat()
        }
        logger.debug(f"Git метрика: {metric_data}")

# Пример конфигурации Git
git_config = {
    "temp_dir": "/tmp/afl_git",
    "git_user": {
        "name": "AFL Orchestrator",
        "email": "orchestrator@company.com"
    },
    "ssh_key_path": "/home/user/.ssh/id_rsa",
    "credentials": {
        "github_token": "ghp_...",
        "gitlab_token": "glpat-..."
    },
    "default_branch": "main",
    "shallow_clone_depth": 1  # Для экономии места
}

# Пример использования
async def example_git_usage():
    git_manager = GitIntegrationManager(git_config)

    # Клонирование репозитория
    repo = await git_manager.clone_repository(
        repo_url="https://github.com/example/repo.git",
        branch="main",
        depth=1,
        clean=True
    )

    if repo:
        # Чтение файла
        content = await git_manager.get_file_content(
            repo=repo,
            file_path="README.md"
        )

        # Получение diff
        changes = await git_manager.get_diff(
            repo=repo,
            base_ref="HEAD~5",
            target_ref="HEAD"
        )

        print(f"Прочитано {len(content or '')} символов из README.md")
        print(f"Найдено {len(changes)} изменений")

        # Очистка после использования
        if repo.local_path.exists():
            shutil.rmtree(repo.local_path)
```

### 6.3 Трекеры задач (Jira, GitHub Issues, Linear)

#### Библиотеки Python

| Система                     | Основная библиотека        | Альтернативы                          |
| --------------------------- | -------------------------- | ------------------------------------- |
| **Jira**                    | `jira` (jira-python)       | `atlassian-python-api` (более полная) |
| **GitHub Issues**           | `github` (PyGithub)        | `aiohttp` для REST API                |
| **Linear**                  | `linear-sdk` (официальная) | `linear-api` (неофициальная)          |
| **Универсальный интерфейс** | Собственная абстракция     | `python-trello` для Trello            |

#### Конкретная реализация с обработкой ошибок

```python
import asyncio
import logging
from typing import Dict, Any, List, Optional
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from datetime import datetime
import backoff
from tenacity import retry, stop_after_attempt, wait_exponential

# Jira
try:
    from jira import JIRA, JIRAError
except ImportError:
    JIRA = None
    JIRAError = Exception

# GitHub
try:
    from github import Github, GithubException
except ImportError:
    Github = None
    GithubException = Exception

logger = logging.getLogger(__name__)

class IssueTrackerType(Enum):
    JIRA = "jira"
    GITHUB = "github"
    LINEAR = "linear"
    GITLAB = "gitlab"

@dataclass
class Issue:
    id: str
    key: str  # Например: PROJ-123
    title: str
    description: str
    status: str
    assignee: Optional[str]
    created_at: datetime
    updated_at: datetime
    url: str
    metadata: Dict[str, Any]

class BaseIssueTracker(ABC):
    """Базовый класс для трекеров задач"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.max_issues_per_request = config.get("max_issues_per_request", 50)
        self.timeout = config.get("timeout", 30.0)

    @abstractmethod
    async def create_issue(
        self,
        project: str,
        title: str,
        description: str,
        **kwargs
    ) -> Optional[Issue]:
        """Создать задачу"""
        pass

    @abstractmethod
    async def update_issue(
        self,
        issue_id: str,
        **updates
    ) -> Optional[Issue]:
        """Обновить задачу"""
        pass

    @abstractmethod
    async def add_comment(
        self,
        issue_id: str,
        comment: str
    ) -> bool:
        """Добавить комментарий к задаче"""
        pass

    @abstractmethod
    async def search_issues(
        self,
        query: str,
        max_results: int = 50
    ) -> List[Issue]:
        """Поиск задач"""
        pass

    async def _handle_tracker_error(
        self,
        error: Exception,
        operation: str,
        context: Dict[str, Any]
    ) -> None:
        """Обработка ошибок трекера"""
        error_type = type(error).__name__
        logger.error(f"Ошибка {operation} в {self.tracker_type.value}: {error}")

        # Запись в метрики
        self._record_error_metric(operation, error_type, context)

        # Повторные попытки для сетевых ошибок
        if any(net_err in str(error).lower() for net_err in ["timeout", "connection", "network"]):
            raise  # Для retry декоратора

class JiraTracker(BaseIssueTracker):
    """Интеграция с Jira"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.tracker_type = IssueTrackerType.JIRA
        self._client = None

        # Параметры подключения
        self.server_url = config["server_url"]
        self.username = config.get("username")
        self.password = config.get("password")
        self.api_token = config.get("api_token")  # Для Cloud Jira

        # Настройки проекта
        self.default_project = config.get("default_project")

    def _get_client(self):
        """Получение клиента Jira (ленивая инициализация)"""
        if self._client is None:
            auth = None
            if self.api_token:
                # Для Jira Cloud
                auth = (self.username, self.api_token)
            elif self.username and self.password:
                # Для Jira Server
                auth = (self.username, self.password)

            try:
                options = {
                    "server": self.server_url,
                    "timeout": self.timeout,
                    "max_retries": 3
                }

                self._client = JIRA(options=options, basic_auth=auth)

                # Проверка подключения
                self._client.myself()
                logger.info(f"Успешно подключено к Jira: {self.server_url}")

            except JIRAError as e:
                logger.error(f"Ошибка подключения к Jira: {e}")
                raise ConnectionError(f"Не удалось подключиться к Jira: {e}")

        return self._client

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    async def create_issue(
        self,
        project: str,
        title: str,
        description: str,
        **kwargs
    ) -> Optional[Issue]:
        """Создать задачу в Jira"""

        project = project or self.default_project
        if not project:
            raise ValueError("Не указан проект Jira")

        loop = asyncio.get_event_loop()

        try:
            # Подготовка полей задачи
            issue_dict = {
                "project": {"key": project},
                "summary": title,
                "description": description,
                "issuetype": {"name": kwargs.get("issue_type", "Task")}
            }

            # Дополнительные поля
            if "assignee" in kwargs:
                issue_dict["assignee"] = {"name": kwargs["assignee"]}
            if "labels" in kwargs:
                issue_dict["labels"] = kwargs["labels"]
            if "priority" in kwargs:
                issue_dict["priority"] = {"name": kwargs["priority"]}

            # Создание задачи
            client = self._get_client()
            jira_issue = await loop.run_in_executor(
                None,
                lambda: client.create_issue(fields=issue_dict)
            )

            # Получение полной информации о задаче
            full_issue = await loop.run_in_executor(
                None,
                lambda: client.issue(jira_issue.key)
            )

            return self._jira_issue_to_model(full_issue)

        except JIRAError as e:
            await self._handle_tracker_error(e, "create_issue", {
                "project": project,
                "title": title[:50] + "..." if len(title) > 50 else title
            })
            return None

    @retry(
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=1, min=1, max=5)
    )
    async def add_comment(self, issue_id: str, comment: str) -> bool:
        """Добавить комментарий в Jira"""

        loop = asyncio.get_event_loop()

        try:
            client = self._get_client()

            # Jira принимает issue key (PROJ-123), а не numeric ID
            await loop.run_in_executor(
                None,
                lambda: client.add_comment(issue_id, comment)
            )

            logger.info(f"Добавлен комментарий к задаче {issue_id}")
            return True

        except JIRAError as e:
            await self._handle_tracker_error(e, "add_comment", {
                "issue_id": issue_id,
                "comment_length": len(comment)
            })
            return False

    async def search_issues(self, query: str, max_results: int = 50) -> List[Issue]:
        """Поиск задач в Jira по JQL"""

        loop = asyncio.get_event_loop()

        try:
            client = self._get_client()

            # Ограничение количества результатов
            max_results = min(max_results, self.max_issues_per_request)

            # Выполнение JQL запроса
            jira_issues = await loop.run_in_executor(
                None,
                lambda: client.search_issues(
                    jql_str=query,
                    maxResults=max_results,
                    fields="*all"
                )
            )

            # Конвертация в модель
            issues = []
            for jira_issue in jira_issues:
                issue_model = self._jira_issue_to_model(jira_issue)
                issues.append(issue_model)

            return issues

        except JIRAError as e:
            await self._handle_tracker_error(e, "search_issues", {
                "query": query,
                "max_results": max_results
            })
            return []

    def _jira_issue_to_model(self, jira_issue) -> Issue:
        """Конвертация объекта Jira в модель Issue"""

        # Извлечение assignee
        assignee = None
        if hasattr(jira_issue.fields, "assignee") and jira_issue.fields.assignee:
            assignee = jira_issue.fields.assignee.displayName

        # Извлечение дат
        created = datetime.strptime(jira_issue.fields.created, "%Y-%m-%dT%H:%M:%S.%f%z")
        updated = datetime.strptime(jira_issue.fields.updated, "%Y-%m-%dT%H:%M:%S.%f%z")

        # Метаданные
        metadata = {
            "project_key": jira_issue.fields.project.key,
            "issue_type": jira_issue.fields.issuetype.name,
            "priority": getattr(jira_issue.fields.priority, "name", None),
            "labels": getattr(jira_issue.fields, "labels", []),
            "status": jira_issue.fields.status.name if jira_issue.fields.status else None
        }

        return Issue(
            id=jira_issue.id,
            key=jira_issue.key,
            title=jira_issue.fields.summary,
            description=jira_issue.fields.description or "",
            status=jira_issue.fields.status.name if jira_issue.fields.status else "Unknown",
            assignee=assignee,
            created_at=created,
            updated_at=updated,
            url=f"{self.server_url}/browse/{jira_issue.key}",
            metadata=metadata
        )

    async def _handle_tracker_error(
        self,
        error: Exception,
        operation: str,
        context: Dict[str, Any]
    ) -> None:
        """Специфичная обработка ошибок Jira"""
        await super()._handle_tracker_error(error, operation, context)

        # Дополнительная обработка для Jira
        error_msg = str(error).lower()

        if "captcha" in error_msg:
            logger.error("Jira требует CAPTCHA. Нужно войти через браузер.")
        elif "rate limit" in error_msg:
            logger.warning("Превышен rate limit Jira. Ожидание...")
            await asyncio.sleep(60)  # Ждём минуту
        elif "permission" in error_msg or "403" in str(error):
            logger.error("Недостаточно прав в Jira. Проверьте разрешения пользователя.")

class GitHubIssuesTracker(BaseIssueTracker):
    """Интеграция с GitHub Issues"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.tracker_type = IssueTrackerType.GITHUB
        self._client = None

        # Параметры подключения
        self.token = config["token"]
        self.default_owner = config.get("default_owner")
        self.default_repo = config.get("default_repo")

    def _get_client(self):
        """Получение клиента GitHub"""
        if self._client is None:
            try:
                self._client = Github(self.token, timeout=self.timeout)

                # Проверка подключения
                self._client.get_user().login
                logger.info("Успешно подключено к GitHub")

            except GithubException as e:
                logger.error(f"Ошибка подключения к GitHub: {e}")
                raise ConnectionError(f"Не удалось подключиться к GitHub: {e}")

        return self._client

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    async def create_issue(
        self,
        project: str,  # В формате "owner/repo"
        title: str,
        description: str,
        **kwargs
    ) -> Optional[Issue]:
        """Создать issue в GitHub"""

        if not project and (self.default_owner and self.default_repo):
            project = f"{self.default_owner}/{self.default_repo}"

        if "/" not in project:
            raise ValueError("Проект должен быть в формате 'owner/repo'")

        owner, repo_name = project.split("/", 1)

        loop = asyncio.get_event_loop()

        try:
            client = self._get_client()

            # Получение репозитория
            repo = await loop.run_in_executor(
                None,
                lambda: client.get_repo(project)
            )

            # Создание issue
            issue_body = description
            if "labels" in kwargs:
                labels = kwargs["labels"]
            else:
                labels = []

            github_issue = await loop.run_in_executor(
                None,
                lambda: repo.create_issue(
                    title=title,
                    body=issue_body,
                    labels=labels
                )
            )

            return self._github_issue_to_model(github_issue, owner, repo_name)

        except GithubException as e:
            await self._handle_tracker_error(e, "create_issue", {
                "project": project,
                "title": title[:50] + "..." if len(title) > 50 else title
            })
            return None

    def _github_issue_to_model(self, github_issue, owner: str, repo: str) -> Issue:
        """Конвертация объекта GitHub в модель Issue"""

        assignee = None
        if github_issue.assignee:
            assignee = github_issue.assignee.login

        metadata = {
            "repository": f"{owner}/{repo}",
            "labels": [label.name for label in github_issue.labels],
            "milestone": github_issue.milestone.title if github_issue.milestone else None,
            "comments_count": github_issue.comments,
            "state": github_issue.state,
            "locked": github_issue.locked
        }

        return Issue(
            id=str(github_issue.id),
            key=f"{owner}/{repo}#{github_issue.number}",
            title=github_issue.title,
            description=github_issue.body or "",
            status=github_issue.state,
            assignee=assignee,
            created_at=github_issue.created_at,
            updated_at=github_issue.updated_at,
            url=github_issue.html_url,
            metadata=metadata
        )

    async def _handle_tracker_error(
        self,
        error: Exception,
        operation: str,
        context: Dict[str, Any]
    ) -> None:
        """Специфичная обработка ошибок GitHub"""
        await super()._handle_tracker_error(error, operation, context)

        error_msg = str(error).lower()

        if "rate limit" in error_msg:
            # GitHub API rate limiting
            logger.warning("Превышен rate limit GitHub. Проверьте лимиты API.")
            # Можно получить информацию о лимитах:
            # limits = self._client.get_rate_limit()
            # reset_time = limits.core.reset

        elif "not found" in error_msg:
            logger.error(f"Репозиторий не найден: {context.get('project')}")

        elif "bad credentials" in error_msg:
            logger.error("Неверный GitHub токен. Проверьте GITHUB_TOKEN.")

# Фабрика трекеров задач
class IssueTrackerFactory:
    """Фабрика для создания трекеров задач"""

    @staticmethod
    def create_tracker(tracker_type: IssueTrackerType, config: Dict[str, Any]) -> BaseIssueTracker:
        """Создать трекер задач указанного типа"""

        if tracker_type == IssueTrackerType.JIRA:
            if JIRA is None:
                raise ImportError("Для Jira интеграции установите 'jira' библиотеку: pip install jira")
            return JiraTracker(config)

        elif tracker_type == IssueTrackerType.GITHUB:
            if Github is None:
                raise ImportError("Для GitHub интеграции установите 'PyGithub': pip install PyGithub")
            return GitHubIssuesTracker(config)

        elif tracker_type == IssueTrackerType.LINEAR:
            try:
                from linear_sdk import LinearClient
                # LinearTracker implementation would go here
                raise NotImplementedError("Linear интеграция в разработке")
            except ImportError:
                raise ImportError("Для Linear интеграции установите 'linear-sdk'")

        else:
            raise ValueError(f"Неподдерживаемый тип трекера: {tracker_type}")

# Пример конфигурации трекеров
tracker_configs = {
    IssueTrackerType.JIRA: {
        "server_url": "https://company.atlassian.net",
        "username": "user@company.com",
        "api_token": "your_api_token",
        "default_project": "PROJ",
        "timeout": 30.0
    },
    IssueTrackerType.GITHUB: {
        "token": "ghp_...",
        "default_owner": "company",
        "default_repo": "repo",
        "timeout": 30.0
    }
}

# Пример использования
async def example_tracker_usage():
    # Создание трекера Jira
    jira_config = tracker_configs[IssueTrackerType.JIRA]
    jira_tracker = IssueTrackerFactory.create_tracker(
        IssueTrackerType.JIRA,
        jira_config
    )

    # Создание задачи
    issue = await jira_tracker.create_issue(
        project="PROJ",
        title="Автоматически созданная задача AFL",
        description="Эта задача создана AFL Orchestrator для отслеживания выполнения workflow.",
        issue_type="Task",
        labels=["afl", "automated"]
    )

    if issue:
        print(f"Создана задача: {issue.key} - {issue.title}")
        print(f"URL: {issue.url}")

        # Добавление комментария
        success = await jira_tracker.add_comment(
            issue_id=issue.key,
            comment="Workflow успешно завершён. Все проверки пройдены."
        )

        if success:
            print("Комментарий добавлен")

    # Поиск задач
    issues = await jira_tracker.search_issues(
        query="project = PROJ AND labels = afl ORDER BY created DESC",
        max_results=10
    )

    print(f"Найдено {len(issues)} задач с меткой 'afl'")
```

### 6.4 Универсальный менеджер интеграций

```python
class IntegrationManager:
    """Центральный менеджер всех интеграций AFL Orchestrator"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config

        # Инициализация менеджеров
        self.llm_manager = LLMIntegrationManager(config.get("llm", {}))
        self.git_manager = GitIntegrationManager(config.get("git", {}))

        # Инициализация трекеров задач
        self.trackers: Dict[IssueTrackerType, BaseIssueTracker] = {}
        tracker_configs = config.get("issue_trackers", {})

        for tracker_type_str, tracker_config in tracker_configs.items():
            try:
                tracker_type = IssueTrackerType(tracker_type_str)
                tracker = IssueTrackerFactory.create_tracker(tracker_type, tracker_config)
                self.trackers[tracker_type] = tracker
                logger.info(f"Инициализирован трекер: {tracker_type.value}")
            except Exception as e:
                logger.error(f"Не удалось инициализировать трекер {tracker_type_str}: {e}")

    async def execute_workflow_step(
        self,
        step_config: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Выполнить шаг workflow с использованием интеграций"""

        step_type = step_config.get("type")
        result = {"success": False, "output": None, "error": None}

        try:
            if step_type == "llm_call":
                result = await self._execute_llm_step(step_config, context)

            elif step_type == "git_operation":
                result = await self._execute_git_step(step_config, context)

            elif step_type == "create_issue":
                result = await self._execute_create_issue_step(step_config, context)

            elif step_type == "add_comment":
                result = await self._execute_add_comment_step(step_config, context)

            else:
                result["error"] = f"Неизвестный тип шага: {step_type}"

        except Exception as e:
            logger.error(f"Ошибка выполнения шага {step_type}: {e}")
            result["error"] = str(e)

        return result

    async def _execute_llm_step(
        self,
        step_config: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Выполнить шаг вызова LLM"""

        messages = step_config.get("messages", [])
        model = step_config.get("model", "gpt-4")

        # Замена переменных контекста в сообщениях
        resolved_messages = self._resolve_context_variables(messages, context)

        response = await self.llm_manager.chat_completion(
            messages=resolved_messages,
            model=model,
            **step_config.get("parameters", {})
        )

        if response:
            return {
                "success": True,
                "output": response.content,
                "metadata": {
                    "model": response.model,
                    "tokens": response.token_usage,
                    "response_time": response.response_time
                }
            }
        else:
            return {
                "success": False,
                "error": "Не удалось получить ответ от LLM"
            }

    async def _execute_git_step(
        self,
        step_config: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Выполнить шаг операции Git"""

        operation = step_config.get("operation")
        repo_url = step_config.get("repository")

        if operation == "clone":
            repo = await self.git_manager.clone_repository(
                repo_url=repo_url,
                branch=step_config.get("branch", "main"),
                depth=step_config.get("depth"),
                clean=step_config.get("clean", True)
            )

            if repo:
                return {
                    "success": True,
                    "output": {
                        "local_path": str(repo.local_path),
                        "branch": repo.branch
                    },
                    "metadata": {
                        "repo_url": repo.repo_url,
                        "operation": "clone"
                    }
                }

        # Другие операции Git...

        return {"success": False, "error": f"Неизвестная операция Git: {operation}"}

    def _resolve_context_variables(
        self,
        messages: List[Dict[str, str]],
        context: Dict[str, Any]
    ) -> List[Dict[str, str]]:
        """Замена переменных контекста в сообщениях"""

        resolved_messages = []

        for message in messages:
            content = message.get("content", "")

            # Замена переменных в формате {{variable}}
            for key, value in context.items():
                if isinstance(value, str):
                    placeholder = f"{{{{{key}}}}}"
                    if placeholder in content:
                        content = content.replace(placeholder, value)

            resolved_messages.append({
                "role": message.get("role", "user"),
                "content": content
            })

        return resolved_messages

# Полная конфигурация интеграций
integration_config = {
    "llm": {
        "api_keys": {
            "openai": "${OPENAI_API_KEY}",
            "anthropic": "${ANTHROPIC_API_KEY}"
        },
        "fallback_models": {
            "gpt-4": "gpt-3.5-turbo-16k",
            "claude-3-opus": "claude-3-sonnet"
        },
        "enable_caching": True,
        "default_timeout": 30.0
    },
    "git": {
        "temp_dir": "/tmp/afl_git",
        "git_user": {
            "name": "AFL Orchestrator",
            "email": "afl@company.com"
        },
        "ssh_key_path": "${SSH_KEY_PATH}",
        "default_branch": "main"
    },
    "issue_trackers": {
        "jira": {
            "server_url": "${JIRA_SERVER_URL}",
            "username": "${JIRA_USERNAME}",
            "api_token": "${JIRA_API_TOKEN}",
            "default_project": "AFL"
        },
        "github": {
            "token": "${GITHUB_TOKEN}",
            "default_owner": "company",
            "default_repo": "projects"
        }
    }
}
```

### 6.5 Резюме по обработке ошибок для всех интеграций

#### Общие паттерны:

1. **Retry с exponential backoff**: Для временных сетевых ошибок
2. **Circuit breaker**: Для предотвращения cascade failures
3. **Fallback стратегии**: Альтернативные модели/сервисы при недоступности
   основных
4. **Детальное логирование**: С контекстом операции для диагностики
5. **Метрики и мониторинг**: Отслеживание успешности и времени операций

#### Специфичные обработки:

- **LLM**: Rate limiting, таймауты, превышение контекста, ошибки аутентификации
- **Git**: Аутентификация SSH/HTTPS, конфликты, недоступность репозиториев
- **Jira/GitHub**: API rate limits, недостаток прав, недоступность проектов

#### Рекомендации для MVP:

1. Начать с **litellm** для LLM абстракции
2. Использовать **gitpython** для Git операций
3. Реализовать **Jira** и **GitHub** интеграции как наиболее востребованные
4. Сфокусироваться на **устойчивости к ошибкам** с первых версий

### 6.6 Игровые движки (Unity, Unreal — если применимо)

**Специфичные use cases**:

- Генерация игрового контента (диалоги, квесты)
- Анализ игрового кода
- Интеграция с редакторами через API

**Будет реализовано как расширение после MVP**.

### 6.7 Прочие инструменты по требованию

**Плагинная система** для быстрого добавления интеграций:

```python
@register_tool(name="slack_send")
class SlackTool:
    """Отправка сообщений в Slack"""

    def __init__(self, token: str):
        self.client = WebClient(token)

    async def execute(self, channel: str, text: str) -> Dict:
        return await self.client.chat_postMessage(channel=channel, text=text)

@register_tool(name="google_docs_read")
class GoogleDocsTool:
    """Чтение Google Docs документов"""

    def __init__(self, credentials_path: str):
        from google.oauth2 import service_account
        from googleapiclient.discovery import build

        credentials = service_account.Credentials.from_service_account_file(
            credentials_path,
            scopes=['https://www.googleapis.com/auth/documents.readonly']
        )
        self.service = build('docs', 'v1', credentials=credentials)

    async def execute(self, document_id: str) -> Dict[str, Any]:
        """Получить содержимое документа"""
        document = self.service.documents().get(documentId=document_id).execute()
        return {
            "title": document.get("title"),
            "content": document.get("body", {}).get("content", [])
        }
```

### 6.8 Service Level Agreements (SLA) для интеграций

| Интеграция        | Операция                   | SLA (p95) | Timeout | Retry  | Fallback           |
| ----------------- | -------------------------- | --------- | ------- | ------ | ------------------ |
| **LLM OpenAI**    | chat_completion            | <15 сек   | 30 сек  | 3 раза | gpt-3.5-turbo      |
| **LLM Anthropic** | chat_completion            | <20 сек   | 45 сек  | 3 раза | claude-3-sonnet    |
| **LLM Local**     | chat_completion            | <30 сек   | 60 сек  | 2 раза | Кэшированный ответ |
| **Git Clone**     | clone_repository (<100 MB) | <30 сек   | 120 сек | 2 раза | shallow clone      |
| **Git Clone**     | clone_repository (>100 MB) | <120 сек  | 300 сек | 2 раза | partial clone      |
| **Git Read**      | get_file_content           | <5 сек    | 15 сек  | 3 раза | кэш                |
| **Git Write**     | commit_and_push            | <10 сек   | 30 сек  | 2 раза | очередь на retry   |
| **Jira**          | create_issue               | <5 сек    | 15 сек  | 3 раза | логирование в БД   |
| **Jira**          | add_comment                | <3 сек    | 10 сек  | 3 раза | логирование в БД   |
| **Jira**          | search_issues              | <10 сек   | 30 сек  | 2 раза | кэш                |
| **GitHub**        | create_issue               | <5 сек    | 15 сек  | 3 раза | логирование в БД   |
| **GitHub**        | add_comment                | <3 сек    | 10 сек  | 3 раза | логирование в БД   |
| **Slack**         | send_message               | <3 сек    | 10 сек  | 3 раза | email уведомление  |
| **Google Docs**   | read_document              | <5 сек    | 15 сек  | 3 раза | кэш                |

#### Детали обработки нарушений SLA:

| Нарушение SLA                | Действие                         | Эскалация                     |
| ---------------------------- | -------------------------------- | ----------------------------- |
| Timeout >1x                  | Логирование, retry               | —                             |
| Timeout >3x подряд           | Circuit breaker (2 мин)          | Уведомление оператора         |
| Error rate >10% за 5 мин     | Fallback на альтернативу         | Уведомление команды           |
| Error rate >50% за 5 мин     | Блокировка интеграции            | Требует ручного вмешательства |
| Полная недоступность >10 мин | Переключение на backup провайдер | Инцидент P2                   |

#### Мониторинг SLA:

```yaml
# Prometheus метрики для SLA
metrics:
  - name: integration_request_duration_seconds
    labels: [integration, operation]
    type: histogram
    buckets: [0.5, 1, 2, 5, 10, 15, 30, 60]

  - name: integration_request_total
    labels: [integration, operation, status]
    type: counter

  - name: integration_circuit_breaker_state
    labels: [integration]
    type: gauge
    values: [0=closed, 1=open, 2=half_open]

  - name: integration_fallback_total
    labels: [integration, fallback_target]
    type: counter

# Алерты
alerts:
  - name: IntegrationSLABreach
    condition: integration_request_duration_seconds:p95 > SLA * 2
    for: 5m
    severity: warning

  - name: IntegrationCircuitOpen
    condition: integration_circuit_breaker_state == 1
    for: 1m
    severity: critical

  - name: IntegrationErrorRateHigh
    condition:
      rate(integration_request_total{status="error"}[5m]) /
      rate(integration_request_total[5m]) > 0.1
    for: 5m
    severity: warning
```

---

## 7. Безопасность (Security)

### 7.1 Аутентификация и авторизация API

**Аутентификация**:

- API keys для машинного доступа
- OAuth 2.0 для пользовательского интерфейса (будущее)
- JWT токены с коротким временем жизни

**Авторизация**:

- RBAC (Role-Based Access Control)
- Разрешения на уровне проектов и workflow
- Аудит всех операций

### 7.2 Хранение секретов (API keys, credentials)

**Подход**:

- Использование HashiCorp Vault или AWS Secrets Manager
- Шифрование чувствительных данных в БД
- Ротация ключей по расписанию

**В MVP**: Шифрование с помощью мастер-ключа, хранимого в env-переменных.

### 7.3 Изоляция выполнения кода агентов (sandbox)

**Уровни изоляции**:

1. **Без изоляции**: Для доверенных агентов
2. **Docker sandbox**: Запуск в отдельном контейнере
3. **gVisor / Firecracker**: Более строгая изоляция

**В MVP**: Docker sandbox для выполнения ненадёжного кода.

### 7.4 Аудит действий (кто, что, когда сделал)

**Таблица аудита**:

```sql
CREATE TABLE audit_log (
    id UUID PRIMARY KEY,
    user_id VARCHAR(255),
    action VARCHAR(50),
    resource_type VARCHAR(50),
    resource_id UUID,
    details JSONB,
    ip_address INET,
    timestamp TIMESTAMP
);
```

**Ретенция логов**: 90 дней для compliance.

---

## 8. Развёртывание (Deployment)

### 8.1 Требования к инфраструктуре

**Минимальные требования (MVP)**:

- CPU: 4 ядра
- RAM: 8 GB
- Storage: 50 GB (SSD)
- Network: 1 Gbps

**Production рекомендации**:

- Kubernetes cluster с 3+ нодами
- Load balancer (nginx-ingress)
- CDN для статических артефактов

### 8.2 Контейнеризация (Docker)

**Dockerfile**:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "orchestrator.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**docker-compose.yml** для локального развёртывания:

```yaml
version: "3.8"
services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: orchestrator
      POSTGRES_USER: orchestrator
      POSTGRES_PASSWORD: changeme

  redis:
    image: redis:7-alpine

  minio:
    image: minio/minio
    command: server /data --console-address ":9001"

  orchestrator:
    build: .
    depends_on:
      - postgres
      - redis
      - minio
    environment:
      DATABASE_URL: postgresql://orchestrator:changeme@postgres/orchestrator
      REDIS_URL: redis://redis:6379
      MINIO_ENDPOINT: minio:9000
```

### 8.3 CI/CD пайплайн для самого оркестратора

**GitHub Actions workflow**:

```yaml
name: CI/CD Pipeline

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v4

      - name: Run tests
        run: |
          pip install -r requirements.txt
          pytest --cov=orchestrator --cov-report=xml

  build-and-push:
    needs: test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'

    steps:
      - name: Build and push Docker image
        run: |
          docker build -t ghcr.io/org/afl-orchestrator:${{ github.sha }} .
          docker push ghcr.io/org/afl-orchestrator:${{ github.sha }}
```

### 8.4 Мониторинг и алертинг (Prometheus, Grafana, etc.)

**Метрики для мониторинга**:

- `workflow_execution_time_seconds`
- `agent_execution_success_rate`
- `token_usage_per_minute`
- `guardrail_violations_total`
- `queue_length`

**Grafana дашборды**:

1. **Обзор системы**: Текущие workflow, нагрузка, ошибки
2. **Бюджет и затраты**: Расход токенов по проектам
3. **Производительность агентов**: Время ответа, успешность

**Алерты**:

- Бюджет превышен на 90%
- Ошибка rate > 5% за 5 минут
- Среднее время выполнения workflow > SLA

---

## 9. План Разработки (Development Roadmap)

### 9.1 Фазы разработки

| Фаза                      | Длительность | Цель                                             |
| ------------------------- | ------------ | ------------------------------------------------ |
| **MVP (6 недель)**        | Недели 1-6   | Базовый рабочий оркестратор с 2-3 типами агентов |
| **Alpha (4 недели)**      | Недели 7-10  | Расширение функциональности, стабилизация        |
| **Beta (4 недели)**       | Недели 11-14 | Пилотные проекты, обратная связь                 |
| **Production (2 недели)** | Недели 15-16 | Подготовка к production-развёртыванию            |

### 9.2 Критерии готовности каждой фазы

**MVP Ready**:

- [ ] Парсинг AFL конфигов и валидация
- [ ] Выполнение простого линейного workflow с 2 агентами
- [ ] Базовые гардрейлы (regex проверки)
- [ ] Учёт токенов и бюджет
- [ ] REST API для запуска workflow
- [ ] Логирование в БД

**Alpha Ready**:

- [ ] Параллельное выполнение шагов
- [ ] LLM-based гардрейлы
- [ ] Контекст менеджер со сжатием
- [ ] Интеграция с Git и Jira
- [ ] Webhook поддержка
- [ ] Docker sandbox для агентов

**Beta Ready**:

- [ ] Пилотные проекты с реальными use cases
- [ ] Производительность: 50+ параллельных workflow
- [ ] UI для мониторинга (базовый)
- [ ] Документация для разработчиков
- [ ] Нагрузочное тестирование

**Production Ready**:

- [ ] High availability развёртывание
- [ ] Полный аудит и безопасность
- [ ] SLA 99.5% availability
- [ ] Disaster recovery план
- [ ] Обучение команды поддержки

### 9.3 Оценка рисков и план митигации

| Риск                                    | Вероятность | Влияние     | Митигация                                                             |
| --------------------------------------- | ----------- | ----------- | --------------------------------------------------------------------- |
| Сложность интеграции с LLM провайдерами | Средняя     | Высокое     | Абстракция провайдеров, fallback стратегии                            |
| Производительность Context Manager      | Высокая     | Среднее     | Кэширование, оптимизация алгоритмов сжатия                            |
| Безопасность sandbox окружения          | Средняя     | Высокое     | Многоуровневая изоляция, аудит безопасности                           |
| Масштабирование БД при высокой нагрузке | Низкая      | Высокое     | Шардирование, read replicas с первого дня                             |
| **Изменение API провайдеров**           | Средняя     | Высокое     | Абстракция litellm, мониторинг changelog, версионирование интеграций  |
| **Превышение бюджета на тестах**        | Высокая     | Среднее     | Лимиты на тестовые вызовы, моки LLM, кэширование ответов              |
| **Задержки LLM >30 сек**                | Высокая     | Высокое     | Circuit breaker, fallback на лёгкие модели, асинхронная очередь       |
| **False positive гардрейлов >5%**       | Средняя     | Высокое     | A/B тестирование правил, быстрое отключение, датасет для валидации    |
| **Vendor lock-in litellm**              | Низкая      | Среднее     | Собственная абстракция поверх litellm, документирование интерфейсов   |
| **Деградация качества LLM**             | Средняя     | Высокое     | Мониторинг quality scores, возможность отката версии модели           |
| **Утечка секретов через агентов**       | Низкая      | Критическое | Гардрейлы на секреты, аудит выводов, принцип минимальных привилегий   |
| **Cascade failure при сбое БД**         | Низкая      | Критическое | Redis кэш для состояний, retry с exponential backoff, circuit breaker |
| **Rate limiting провайдеров**           | Высокая     | Высокое     | Квотирование на workflow, приоритизация, кэширование, пул API ключей  |
| **Потеря контекста при сбое**           | Средняя     | Высокое     | Периодический snapshot состояния, WAL логирование                     |
| **Сложность отладки workflow**          | Высокая     | Среднее     | Детальное логирование, replay режим, пошаговая отладка                |

### 9.4 Матрица сложностей реализации

| Компонент        | Ожидаемая сложность | Реальная сложность | Комментарий                              |
| ---------------- | ------------------- | ------------------ | ---------------------------------------- |
| Parser Module    | 🟢 Низкая           | 🟢 Низкая          | Pydantic упрощает валидацию              |
| Workflow Engine  | 🟡 Средняя          | 🟡 Средняя         | State machine хорошо документирован      |
| Context Manager  | 🟡 Средняя          | 🔴 Высокая         | ML-суммаризация требует экспертизы       |
| Guardrail Engine | 🟡 Средняя          | 🔴 Высокая         | LLM-as-a-Judge дорогой и медленный       |
| Budget Tracker   | 🟢 Низкая           | 🟡 Средняя         | Точный учёт токенов требует интеграции   |
| Agent Executor   | 🟡 Средняя          | 🟡 Средняя         | Интеграции требуют обработки ошибок      |
| Docker Sandbox   | 🟡 Средняя          | 🔴 Высокая         | Безопасность требует глубоких знаний     |
| LLM Integration  | 🟢 Низкая           | 🟡 Средняя         | Множество специфичных ошибок провайдеров |

### 9.5 Зависимости и внешние блокираторы

**Внутренние зависимости**:

1. AI Team → Реализация LLM-агентов и гардрейлов
2. Platform Team → Инфраструктура и CI/CD
3. Security Team → Аудит и безопасность

**Внешние зависимости**:

1. LLM провайдеры → API stability, rate limits
2. Интеграционные партнёры (GitHub, Jira) → API доступность
3. Cloud провайдер → Инфраструктурная доступность

---

## 10. Тестирование (Testing Strategy)

### 10.1 Юнит-тесты для компонентов

**Покрытие кода > 80%**:

- Parser: Валидация различных AFL конфигов
- Workflow Engine: Тесты состояний и переходов
- Guardrail Engine: Проверка всех типов гардрейлов
- Budget Tracker: Расчёт затрат и лимитов

**Фреймворк**: pytest + pytest-asyncio

### 10.2 Интеграционные тесты (агенты + оркестратор)

**Тестовые сценарии**:

1. Полный цикл выполнения workflow с моками LLM
2. Интеграция с реальными системами (Git, Jira) в test окружении
3. Проверка восстановления после сбоев БД/сети

**Test doubles**: Mock LLM провайдеры, fake инструменты

### 10.3 End-to-End тесты workflow

**Реальные AFL конфиги** для типичных use cases:

- Code review workflow
- Content generation workflow
- Data analysis workflow

**Метрики**:

- Успешное завершение workflow
- Соответствие гардрейлам
- Соответствие бюджету

### 10.4 Нагрузочное тестирование

**Tools**: Locust или k6

**Сценарии**:

1. Постепенное увеличение нагрузки: 10 → 100 → 1000 параллельных workflow
2. Длительное тестирование на стабильной нагрузке (24 часа)
3. Spike тестирование: резкое увеличение нагрузки в 10 раз

**Целевые метрики**:

- Latency p95 < 2s
- Throughput > 100 workflow/мин
- Error rate < 1%

### 10.5 Тесты на безопасность гардрейлов

**Тестовые атаки**:

- Prompt injection attempts
- Data leakage attempts
- Resource exhaustion attacks

**Оценка эффективности**:

- False positive rate < 5%
- False negative rate < 1%
- Производительность: проверка за < 100мс

---

## Приложения

### Приложение A: Пример AFL конфига для code review

```yaml
version: "1.0"
project: "automated_code_review"
budget:
  total_tokens: 50000
  warning_threshold: 0.8

agents:
  - id: "code_fetcher"
    type: "git"
    repository: "${REPO_URL}"
    branch: "main"

  - id: "static_analyzer"
    type: "llm"
    model: "gpt-4"
    system_prompt: |
      Ты — Senior разработчик, анализирующий код на наличие:
      1. Безопасностных уязвимостей
      2. Ошибок архитектуры
      3. Нарушений code style
    temperature: 0.1

  - id: "review_writer"
    type: "llm"
    model: "claude-3-opus"
    system_prompt: |
      Ты пишешь конструктивные code review комментарии.
      Будь вежливым, конкретным, предлагай решения.
    temperature: 0.3

artifacts:
  - id: "source_code"
    type: "directory"
    path: "./code"

  - id: "static_analysis"
    type: "json"
    path: "./reports/analysis.json"

  - id: "review_comments"
    type: "markdown"
    path: "./reports/review.md"

guardrails:
  - id: "no_secrets"
    type: "regex"
    pattern: '(?i)(password|api[_-]?key|secret|token)=[''"][^''"]+[''"]'
    action: "block"

  - id: "professional_tone"
    type: "llm_judge"
    prompt:
      "Оцени тон текста по шкале от 1 (непрофессиональный) до 10
      (профессиональный)"
    threshold: 7
    model: "gpt-4"

workflow:
  - step: "fetch_code"
    agent: "code_fetcher"
    artifact: "source_code"

  - step: "analyze"
    agent: "static_analyzer"
    depends_on: ["fetch_code"]
    artifact: "static_analysis"

  - step: "write_review"
    agent: "review_writer"
    depends_on: ["analyze"]
    artifact: "review_comments"
    guardrails: ["professional_tone"]
```

### Приложение B: Схема базы данных (SQL)

```sql
-- Полная схема БД находится в файле schema.sql
-- Основные таблицы описаны в разделе 3.1

-- Индексы для производительности:
CREATE INDEX idx_workflow_execution_status ON workflow_execution(status);
CREATE INDEX idx_agent_execution_task ON agent_execution(task_execution_id);
CREATE INDEX idx_cost_record_workflow ON cost_record(workflow_execution_id);
CREATE INDEX idx_audit_log_timestamp ON audit_log(timestamp DESC);
```

### Приложение C: API Reference (OpenAPI 3.0)

Полная спецификация OpenAPI доступна по пути `/docs` в работающем оркестраторе.

---

## Глоссарий

| Термин          | Определение                                                                  |
| --------------- | ---------------------------------------------------------------------------- |
| **AFL**         | Agentic Flow Language — декларативный язык описания мульти-агентных workflow |
| **Оркестратор** | Система, исполняющая AFL конфиги и управляющая агентами                      |
| **Агент**       | Автономный программный компонент (чаще всего LLM-based)                      |
| **Артефакт**    | Ресурс, создаваемый или используемый в workflow                              |
| **Гардрейл**    | Правило безопасности или качества                                            |
| **Workflow**    | Последовательность шагов выполнения                                          |
| **Контекст**    | Информация, передаваемая между агентами                                      |

---

_Документ подготовлен в соответствии с требованиями TASK.md. Все разделы
заполнены с фокусом на реализуемость MVP._
