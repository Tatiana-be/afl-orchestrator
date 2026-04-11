# AFL Orchestrator: Полная Спецификация API

**Версия**: 1.1 **Дата**: 2026-04-10 **Статус**: Approved for Development
**Автор**: Backend Lead & API Architect

**Changelog v1.1 (AFL-101)**:
- Unified workflow status enum to 7 values: `pending, queued, running, paused, completed, failed, cancelled`
- Added `error_code` and `error_message` fields to workflow responses
- Initial status for POST /workflows response: `pending`
- Added 8 webhook events covering all status transitions
- Added workflow status reference table and error_code documentation
- Added `queued` and `pending` to GET /workflows query parameter filter

---

## 1. Общие Принципы API Дизайна

### 1.1 Архитектурный стиль

| Аспект              | Решение                                 |
| ------------------- | --------------------------------------- |
| **Стиль**           | RESTful + WebSocket (real-time)         |
| **Версионирование** | URL Path: `/api/v1/`, `/api/v2/`        |
| **Формат данных**   | JSON (UTF-8)                            |
| **Аутентификация**  | Bearer Token (JWT)                      |
| **Пагинация**       | Cursor-based для списков >100 элементов |
| **Кодировка**       | UTF-8                                   |
| **Время**           | ISO 8601 (UTC)                          |

### 1.2 Базовые URL

| Окружение       | URL                                               |
| --------------- | ------------------------------------------------- |
| **Development** | `https://dev-api.afl-orchestrator.local/api/v1`   |
| **Staging**     | `https://staging-api.afl-orchestrator.com/api/v1` |
| **Production**  | `https://api.afl-orchestrator.com/api/v1`         |
| **WebSocket**   | `wss://api.afl-orchestrator.com/api/v1/ws`        |

### 1.3 Стандартные HTTP коды

| Код | Значение              | Когда используется               |
| --- | --------------------- | -------------------------------- |
| 200 | OK                    | Успешный GET, PUT, PATCH         |
| 201 | Created               | Успешный POST (создание ресурса) |
| 202 | Accepted              | Асинхронная операция принята     |
| 204 | No Content            | Успешное удаление                |
| 400 | Bad Request           | Неверный формат запроса          |
| 401 | Unauthorized          | Отсутствует или неверный токен   |
| 403 | Forbidden             | Недостаточно прав                |
| 404 | Not Found             | Ресурс не найден                 |
| 409 | Conflict              | Конфликт состояния               |
| 422 | Unprocessable Entity  | Ошибка валидации                 |
| 429 | Too Many Requests     | Превышен rate limit              |
| 500 | Internal Server Error | Внутренняя ошибка сервера        |
| 503 | Service Unavailable   | Сервис недоступен                |

### 1.4 Формат ошибок

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Человекочитаемое описание ошибки",
    "details": { "field": "additional context" },
    "timestamp": "2026-03-31T10:30:00Z",
    "request_id": "req-abc123",
    "documentation_url": "https://docs.afl-orchestrator.com/errors/ERROR_CODE"
  }
}
```

### 1.5 Пагинация (Cursor-based)

**Запрос:** `GET /api/v1/workflows?cursor=eyJpZCI6MTAwfQ&limit=20`

**Ответ:**

```json
{
  "data": [...],
  "pagination": {
    "cursor": "eyJpZCI6MTAwfQ",
    "next_cursor": "eyJpZCI6MTQwfQ",
    "prev_cursor": "eyJpZCI6MTAwfQ",
    "limit": 20,
    "has_more": true
  }
}
```

### 1.6 Rate Limiting

| Tier           | Requests/мин | Requests/час | Burst |
| -------------- | ------------ | ------------ | ----- |
| **Free**       | 30           | 500          | 10    |
| **Pro**        | 100          | 5000         | 30    |
| **Enterprise** | 500          | 50000        | 100   |

**Headers:** `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`,
`Retry-After`

---

## 2. Категории Эндпоинтов

### 2.1 Управление Проектами (Projects)

| Endpoint                  | Method   | MVP | Описание           |
| ------------------------- | -------- | --- | ------------------ |
| `/projects`               | POST     | ✅  | Создание проекта   |
| `/projects`               | GET      | ✅  | Список проектов    |
| `/projects/{id}`          | GET      | ✅  | Детали проекта     |
| `/projects/{id}`          | PUT      | ✅  | Обновление проекта |
| `/projects/{id}`          | DELETE   | ✅  | Удаление проекта   |
| `/projects/{id}/settings` | GET/PUT  | 🟡  | Настройки проекта  |
| `/projects/{id}/members`  | GET/POST | 🟡  | Участники проекта  |

#### POST /api/v1/projects

```yaml
Endpoint: POST /api/v1/projects
Summary: Создание нового проекта
Authentication: Bearer Token (требуется)
Rate Limit: 10 запросов/минуту
Idempotency: Key через header `Idempotency-Key`

Request Body:
  type: object
  required: [name]
  properties:
    name: { type: string, minLength: 1, maxLength: 100 }
    description: { type: string, maxLength: 500 }
    default_budget:
      type: object
      properties:
        total_tokens: { type: integer }
        warning_threshold: { type: number, min: 0, max: 1 }

Response 201:
  type: object
  properties:
    project_id: { type: string, format: uuid }
    name: { type: string }
    created_at: { type: string, format: date-time }
    created_by: { type: string }
```

#### GET /api/v1/projects

```yaml
Endpoint: GET /api/v1/projects
Summary: Список проектов пользователя
Authentication: Bearer Token (требуется)
Rate Limit: 30 запросов/минуту

Query Parameters:
  - cursor: string (optional)
  - limit: integer, default=20, min=1, max=100
  - sort: enum [created_at, name, updated_at], default="created_at"
  - order: enum [asc, desc], default="desc"
  - status: enum [active, archived, all], default="active"

Response 200:
  type: object
  properties:
    data: { type: array, items: { $ref: ProjectSummary } }
    pagination: { $ref: Pagination }
```

---

### 2.2 Управление Конфигами AFL (Configs)

| Endpoint                                | Method | MVP | Описание          |
| --------------------------------------- | ------ | --- | ----------------- |
| `/projects/{id}/configs`                | POST   | ✅  | Загрузка конфига  |
| `/projects/{id}/configs`                | GET    | ✅  | Список версий     |
| `/projects/{id}/configs/{version}`      | GET    | ✅  | Получение версии  |
| `/projects/{id}/configs/validate`       | POST   | ✅  | Валидация конфига |
| `/projects/{id}/configs/{v1}/diff/{v2}` | GET    | 🟡  | Сравнение версий  |
| `/projects/{id}/configs/latest`         | GET    | ✅  | Последняя версия  |

#### POST /api/v1/projects/{id}/configs

```yaml
Endpoint: POST /api/v1/projects/{id}/configs
Summary: Загрузка нового AFL конфига
Authentication: Bearer Token (требуется)
Rate Limit: 10 запросов/минуту

Request Body:
  type: object
  required: [content]
  properties:
    content: { type: string, description: "YAML или JSON контент" }
    format: { type: string, enum: [yaml, json], default: "yaml" }
    version:
      { type: string, description: "Semver, автогенерация если не указано" }
    changelog: { type: string, maxLength: 500 }

Response 201:
  type: object
  properties:
    config_id: { type: string }
    project_id: { type: string }
    version: { type: string }
    validation_status: { type: string, enum: [valid, invalid, warnings] }
    validation_errors: { type: array }
```

#### POST /api/v1/projects/{id}/configs/validate

```yaml
Endpoint: POST /api/v1/projects/{id}/configs/validate
Summary: Валидация AFL конфига без сохранения
Authentication: Bearer Token (требуется)
Rate Limit: 20 запросов/минуту

Request Body:
  type: object
  required: [content]
  properties:
    content: { type: string }
    format: { type: string, enum: [yaml, json], default: "yaml" }
    strict: { type: boolean, default: false }

Response 200:
  type: object
  properties:
    valid: { type: boolean }
    status: { type: string, enum: [valid, invalid, warnings] }
    errors: { type: array, items: { line, column, message, code } }
    warnings: { type: array }
    parsed_config: { type: object }
```

---

### 2.3 Управление Workflow (Workflows)

| Endpoint                    | Method | MVP | Описание           |
| --------------------------- | ------ | --- | ------------------ |
| `/workflows`                | POST   | ✅  | Запуск workflow    |
| `/workflows`                | GET    | ✅  | Список workflow    |
| `/workflows/{id}`           | GET    | ✅  | Статус workflow    |
| `/workflows/{id}`           | DELETE | ✅  | Отмена workflow    |
| `/workflows/{id}/pause`     | POST   | ✅  | Приостановка       |
| `/workflows/{id}/resume`    | POST   | ✅  | Возобновление      |
| `/workflows/{id}/retry`     | POST   | ✅  | Повтор failed шага |
| `/workflows/{id}/steps`     | GET    | ✅  | Список шагов       |
| `/workflows/{id}/artifacts` | GET    | ✅  | Артефакты workflow |

#### POST /api/v1/workflows

```yaml
Endpoint: POST /api/v1/workflows
Summary: Запуск нового workflow
Authentication: Bearer Token (требуется)
Rate Limit: 10 запросов/минуту
Idempotency: Key через header `Idempotency-Key`

Request Body:
  type: object
  required: [project_id, config_version]
  properties:
    project_id: { type: string, format: uuid }
    config_version: { type: string }
    parameters: { type: object }
    priority:
      { type: string, enum: [low, normal, high, critical], default: "normal" }
    webhook_url: { type: string, format: uri }
    metadata: { type: object }

Response 201 Created:
  type: object
  properties:
    workflow_id: { type: string, format: uuid }
    project_id: { type: string }
    status: { type: string, enum: [pending] }
    error_code: { type: string, nullable: true }
    error_message: { type: string, nullable: true }
    created_at: { type: string, format: date-time }
    estimated_queue_time_seconds: { type: integer }
    status_url: { type: string, format: uri }

Note: Initial status always `pending` after creation.

WebSocket Events:
  - workflow.pending
  - workflow.queued
  - workflow.running
  - workflow.paused
  - workflow.resumed
  - workflow.completed
  - workflow.failed
  - workflow.cancelled
```

#### GET /api/v1/workflows

```yaml
Endpoint: GET /api/v1/workflows
Summary: Список workflow
Authentication: Bearer Token (требуется)
Rate Limit: 30 запросов/минуту

Query Parameters:
  - cursor: string (optional)
  - limit: integer, default=20, min=1, max=100
  - project_id: string (optional)
  - status: enum [pending, queued, running, paused, completed, failed, cancelled]
  - config_version: string (optional)
  - created_from: string, format=date-time
  - created_to: string, format=date-time
  - sort: enum [created_at, updated_at, duration], default="created_at"
  - order: enum [asc, desc], default="desc"

Response 200:
  type: object
  properties:
    data: { type: array, items: { $ref: WorkflowSummary } }
    pagination: { $ref: Pagination }
```

#### GET /api/v1/workflows/{id}

```yaml
Endpoint: GET /api/v1/workflows/{id}
Summary: Детали workflow
Authentication: Bearer Token (требуется)
Rate Limit: 30 запросов/минуту

Response 200:
  type: object
  properties:
    workflow_id: { type: string }
    project_id: { type: string }
    config_version: { type: string }
    status:
      {
        type: string,
        enum: [pending, queued, running, paused, completed, failed, cancelled],
      }
    error_code:
      { type: string, enum: [guardrail_violation, budget_exceeded, agent_error, system_error, cancelled_by_user], nullable: true }
    error_message: { type: string, nullable: true }
    progress: { type: number, min: 0, max: 1 }
    current_step: { type: string, nullable: true }
    total_steps: { type: integer }
    completed_steps: { type: integer }
    failed_steps: { type: integer }
    created_at: { type: string, format: date-time }
    started_at: { type: string, format: date-time, nullable: true }
    updated_at: { type: string, format: date-time }
    paused_at: { type: string, format: date-time, nullable: true }
    completed_at: { type: string, format: date-time, nullable: true }
    failed_at: { type: string, format: date-time, nullable: true }
    cancelled_at: { type: string, format: date-time, nullable: true }
    estimated_duration: { type: integer }
    elapsed_time: { type: integer }
    tokens_used: { type: integer }
    cost_usd: { type: number }
    parameters: { type: object }
    metadata: { type: object }
    steps: { type: array, items: { $ref: WorkflowStep } }
    artifacts: { type: array, items: { $ref: ArtifactSummary } }
    errors: { type: array, items: { $ref: WorkflowError } }
```

#### POST /api/v1/workflows/{id}/pause

```yaml
Endpoint: POST /api/v1/workflows/{id}/pause
Summary: Приостановка workflow
Authentication: Bearer Token (требуется)
Rate Limit: 10 запросов/минуту

Request Body:
  type: object
  properties:
    reason: { type: string, maxLength: 200 }

Response 200:
  type: object
  properties:
    workflow_id: { type: string }
    status: { type: string, enum: ["paused"] }
    paused_at: { type: string, format: date-time }
    paused_by: { type: string }
    current_step: { type: string }
    can_resume: { type: boolean }
```

#### POST /api/v1/workflows/{id}/resume

```yaml
Endpoint: POST /api/v1/workflows/{id}/resume
Summary: Возобновление workflow
Authentication: Bearer Token (требуется)
Rate Limit: 10 запросов/минуту

Request Body:
  type: object
  properties:
    parameters: { type: object, description: "Обновлённые параметры" }

Response 200:
  type: object
  properties:
    workflow_id: { type: string }
    status: { type: string, enum: ["running"] }
    resumed_at: { type: string, format: date-time }
    resumed_by: { type: string }
    current_step: { type: string }
```

#### POST /api/v1/workflows/{id}/retry

```yaml
Endpoint: POST /api/v1/workflows/{id}/retry
Summary: Повтор failed шага
Authentication: Bearer Token (требуется)
Rate Limit: 5 запросов/минуту

Request Body:
  type: object
  required: [step_id]
  properties:
    step_id: { type: string }
    parameters: { type: object }
    skip_guardrails: { type: boolean, default: false }

Response 202:
  type: object
  properties:
    workflow_id: { type: string }
    step_id: { type: string }
    status: { type: string, enum: ["retrying"] }
    retry_count: { type: integer }
    max_retries: { type: integer }
    started_at: { type: string, format: date-time }
```

#### DELETE /api/v1/workflows/{id}

```yaml
Endpoint: DELETE /api/v1/workflows/{id}
Summary: Отмена workflow
Authentication: Bearer Token (требуется)
Rate Limit: 10 запросов/минуту
Idempotency: Идемпотентный

Query Parameters:
  - force: boolean, default=false

Request Body:
  type: object
  properties:
    reason: { type: string, maxLength: 200 }

Response 204: No Content
```

#### 2.3.1 Workflow Status Reference

| Status | HTTP Webhook | Client-facing description |
|--------|--------------|---------------------------|
| pending | workflow.pending | Created, awaiting scheduler assignment |
| queued | workflow.queued | Scheduled, waiting for executor |
| running | workflow.running | Currently executing |
| paused | workflow.paused | Suspended by user |
| completed | workflow.completed | Successfully finished |
| failed | workflow.failed | Error occurred (see `error_code`) |
| cancelled | workflow.cancelled | Cancelled by user or system |

#### 2.3.2 Error Codes

| error_code | Description | Retryable | Action |
|------------|-------------|-----------|--------|
| guardrail_violation | Security guardrail violated | ❌ | Fix configuration |
| budget_exceeded | Token budget exceeded | ❌ | Increase budget |
| agent_error | Agent error (timeout, exception) | ✅ | Auto-retry |
| system_error | System error (DB, network) | ✅ | Auto-retry |
| cancelled_by_user | Cancelled by user | ❌ | — |

⚠️ **Note:** `budget_exceeded` is an `error_code`, **not** a workflow status.
When budget is exceeded, the workflow transitions to `failed` with `error_code: budget_exceeded`.

---

### 2.4 Управление Агентами (Agents)

| Endpoint               | Method | MVP | Описание                |
| ---------------------- | ------ | --- | ----------------------- |
| `/agents`              | GET    | ✅  | Список активных агентов |
| `/agents/{id}`         | GET    | ✅  | Детали агента           |
| `/agents/{id}/logs`    | GET    | ✅  | Логи агента             |
| `/agents/{id}/history` | GET    | ✅  | История действий        |
| `/agents/{id}/restart` | POST   | 🟡  | Перезапуск агента       |
| `/agents/pool/stats`   | GET    | ✅  | Статистика пула         |
| `/agents/types`        | GET    | ✅  | Типы агентов            |

#### GET /api/v1/agents

```yaml
Endpoint: GET /api/v1/agents
Summary: Список активных агентов
Authentication: Bearer Token (требуется)
Rate Limit: 30 запросов/минуту

Query Parameters:
  - cursor: string
  - limit: integer, default=20, min=1, max=100
  - status: enum [idle, busy, error, offline]
  - type: string
  - project_id: string
  - sort: enum [created_at, last_active, tasks_completed], default="last_active"
  - order: enum [asc, desc], default="desc"

Response 200:
  type: object
  properties:
    data: { type: array, items: { $ref: Agent } }
    pagination: { $ref: Pagination }
    summary:
      type: object
      properties:
        total: { type: integer }
        idle: { type: integer }
        busy: { type: integer }
        error: { type: integer }
        offline: { type: integer }
```

#### GET /api/v1/agents/{id}

```yaml
Endpoint: GET /api/v1/agents/{id}
Summary: Детали агента
Authentication: Bearer Token (требуется)
Rate Limit: 30 запросов/минуту

Response 200:
  type: object
  properties:
    agent_id: { type: string }
    name: { type: string }
    type: { type: string }
    model: { type: string }
    status: { type: string, enum: [idle, busy, error, offline] }
    config: { $ref: AgentConfig }
    current_task: { $ref: CurrentTask, nullable: true }
    metrics: { $ref: AgentMetrics }
    capabilities: { type: array, items: string }
    tools: { type: array, items: string }
    created_at: { type: string, format: date-time }
    last_active: { type: string, format: date-time }
    health: { $ref: AgentHealth }
```

#### GET /api/v1/agents/{id}/logs

```yaml
Endpoint: GET /api/v1/agents/{id}/logs
Summary: Логи агента
Authentication: Bearer Token (требуется)
Rate Limit: 20 запросов/минуту

Query Parameters:
  - cursor: string
  - limit: integer, default=50, min=1, max=200
  - level: enum [debug, info, warning, error, critical]
  - from: string, format=date-time
  - to: string, format=date-time
  - workflow_id: string
  - search: string, maxLength=100

Response 200:
  type: object
  properties:
    data: { type: array, items: { $ref: LogEntry } }
    pagination: { $ref: Pagination }
```

---

### 2.5 Артефакты (Artifacts)

| Endpoint                      | Method  | MVP | Описание             |
| ----------------------------- | ------- | --- | -------------------- |
| `/workflows/{id}/artifacts`   | GET     | ✅  | Список артефактов    |
| `/artifacts/{id}`             | GET     | ✅  | Детали артефакта     |
| `/artifacts/{id}/download`    | GET     | ✅  | Скачивание артефакта |
| `/artifacts/{id}/versions`    | GET     | 🟡  | Версии артефакта     |
| `/artifacts/{id}/permissions` | GET/PUT | 🟡  | Доступ к артефакту   |

#### GET /api/v1/workflows/{id}/artifacts

```yaml
Endpoint: GET /api/v1/workflows/{id}/artifacts
Summary: Список артефактов workflow
Authentication: Bearer Token (требуется)
Rate Limit: 30 запросов/минуту

Query Parameters:
  - type: string (filter by type)
  - step_id: string (filter by step)

Response 200:
  type: object
  properties:
    data: { type: array, items: { $ref: Artifact } }
```

#### GET /api/v1/artifacts/{id}/download

```yaml
Endpoint: GET /api/v1/artifacts/{id}/download
Summary: Скачивание артефакта
Authentication: Bearer Token (требуется)
Rate Limit: 50 запросов/минуту

Query Parameters:
  - inline: boolean, default=false
  - expires: integer, default=3600, min=60, max=86400

Response 200:
  type: object
  properties:
    artifact_id: { type: string }
    name: { type: string }
    download_url: { type: string, format: uri }
    expires_at: { type: string, format: date-time }
    size_bytes: { type: integer }
    content_type: { type: string }
```

---

### 2.6 Бюджет и Метрики (Budget & Metrics)

| Endpoint                        | Method   | MVP | Описание                |
| ------------------------------- | -------- | --- | ----------------------- |
| `/projects/{id}/budget`         | GET      | ✅  | Текущий бюджет          |
| `/projects/{id}/budget`         | PUT      | ✅  | Обновление лимитов      |
| `/projects/{id}/metrics/tokens` | GET      | ✅  | Расход токенов          |
| `/projects/{id}/metrics/cost`   | GET      | ✅  | Затраты USD             |
| `/projects/{id}/metrics/usage`  | GET      | ✅  | Детальное использование |
| `/projects/{id}/metrics/export` | GET      | 🟡  | Экспорт отчёта          |
| `/budget/alerts`                | GET/POST | ✅  | Управление алертами     |

#### GET /api/v1/projects/{id}/budget

```yaml
Endpoint: GET /api/v1/projects/{id}/budget
Summary: Текущий бюджет проекта
Authentication: Bearer Token (требуется)
Rate Limit: 30 запросов/минуту

Response 200:
  type: object
  properties:
    project_id: { type: string }
    budget:
      type: object
      properties:
        total_tokens: { type: integer }
        used_tokens: { type: integer }
        remaining_tokens: { type: integer }
        usage_percentage: { type: number }
        warning_threshold: { type: number }
        hard_limit: { type: integer }
    cost:
      type: object
      properties:
        total_usd: { type: number }
        used_usd: { type: number }
        remaining_usd: { type: number }
    forecast:
      type: object
      properties:
        estimated_total_tokens: { type: integer }
        estimated_total_usd: { type: number }
        days_until_limit: { type: integer }
        active_workflows_tokens: { type: integer }
    breakdown:
      type: object
      properties:
        by_model: { type: array }
        by_workflow: { type: array }
        by_agent: { type: array }
    period:
      type: object
      properties:
        from: { type: string, format: date }
        to: { type: string, format: date }
```

#### POST /api/v1/budget/alerts

```yaml
Endpoint: POST /api/v1/budget/alerts
Summary: Создание алерта бюджета
Authentication: Bearer Token (требуется)
Rate Limit: 10 запросов/минуту

Request Body:
  type: object
  required: [project_id, alert_type, threshold, notification_channels]
  properties:
    project_id: { type: string }
    alert_type: { type: string, enum: [percentage, absolute, forecast] }
    threshold: { type: number }
    notification_channels:
      { type: array, items: { enum: [email, slack, webhook] } }
    webhook_url: { type: string, format: uri }
    enabled: { type: boolean, default: true }
    message_template: { type: string, maxLength: 500 }

Response 201:
  type: object
  properties:
    alert_id: { type: string }
    project_id: { type: string }
    alert_type: { type: string }
    threshold: { type: number }
    enabled: { type: boolean }
    created_at: { type: string, format: date-time }
    created_by: { type: string }
```

---

### 2.7 События и Уведомления (Events & Webhooks)

| Endpoint                               | Method         | MVP | Описание           |
| -------------------------------------- | -------------- | --- | ------------------ |
| `/events`                              | GET            | ✅  | Список событий     |
| `/webhooks`                            | GET/POST       | ✅  | Управление webhook |
| `/webhooks/{id}`                       | GET/PUT/DELETE | ✅  | Webhook детали     |
| `/webhooks/{id}/test`                  | POST           | ✅  | Тест webhook       |
| `/webhooks/{id}/deliveries`            | GET            | ✅  | История доставок   |
| `/webhooks/{id}/deliveries/{id}/retry` | POST           | ✅  | Повтор доставки    |

#### GET /api/v1/events

```yaml
Endpoint: GET /api/v1/events
Summary: Список доступных событий
Authentication: Bearer Token (требуется)
Rate Limit: 30 запросов/минуту

Response 200:
  type: object
  properties:
    events:
      type: array
      items:
        type: object
        properties:
          name: { type: string }
          description: { type: string }
          category: { type: string }
          payload_schema: { type: object }
          example: { type: object }

Available Events:
  Workflow:
    workflow.pending, workflow.queued, workflow.running, workflow.paused,
    workflow.resumed, workflow.completed, workflow.failed, workflow.cancelled,
    workflow.step_completed, workflow.step_failed
  Budget: budget.warning, budget.exceeded, budget.updated
  Agent: agent.created, agent.destroyed, agent.error, agent.idle, agent.busy
  Config: config.created, config.updated, config.validated
  Security: guardrail.violation, auth.login, auth.logout, auth.failed
```

#### POST /api/v1/webhooks

```yaml
Endpoint: POST /api/v1/webhooks
Summary: Создание webhook
Authentication: Bearer Token (требуется)
Rate Limit: 10 запросов/минуту

Request Body:
  type: object
  required: [project_id, url, events, secret]
  properties:
    project_id: { type: string }
    url: { type: string, format: uri }
    events: { type: array, items: string }
    secret: { type: string, minLength: 16, description: "HMAC secret" }
    active: { type: boolean, default: true }
    headers: { type: object }
    retry_policy:
      type: object
      properties:
        max_retries: { type: integer, default: 3 }
        backoff_seconds: { type: integer, default: 60 }

Response 201:
  type: object
  properties:
    webhook_id: { type: string }
    project_id: { type: string }
    url: { type: string }
    events: { type: array }
    active: { type: boolean }
    created_at: { type: string, format: date-time }
    created_by: { type: string }
```

#### POST /api/v1/webhooks/{id}/test

```yaml
Endpoint: POST /api/v1/webhooks/{id}/test
Summary: Тестовая отправка webhook
Authentication: Bearer Token (требуется)
Rate Limit: 5 запросов/минуту

Request Body:
  type: object
  properties:
    event: { type: string, default: "workflow.started" }

Response 200:
  type: object
  properties:
    webhook_id: { type: string }
    delivery_id: { type: string }
    event: { type: string }
    status: { type: string, enum: [sent, failed] }
    http_status: { type: integer, nullable: true }
    response_time_ms: { type: integer }
    sent_at: { type: string, format: date-time }
    payload: { type: object }
```

---

### 2.8 Администрирование (Admin)

| Endpoint                  | Method | MVP | Описание               |
| ------------------------- | ------ | --- | ---------------------- |
| `/admin/users`            | GET    | 🟡  | Список пользователей   |
| `/admin/users/{id}`       | GET    | 🟡  | Детали пользователя    |
| `/admin/users/{id}/roles` | PUT    | 🟡  | Обновление роли        |
| `/admin/audit-logs`       | GET    | ✅  | Аудит действий         |
| `/admin/system/health`    | GET    | ✅  | Health check           |
| `/admin/system/config`    | GET    | 🟡  | Системная конфигурация |
| `/admin/rate-limits`      | GET    | 🟡  | Статистика rate limits |

#### GET /api/v1/admin/audit-logs

```yaml
Endpoint: GET /api/v1/admin/audit-logs
Summary: Аудит действий
Authentication: Bearer Token (требуется, роль: admin)
Rate Limit: 20 запросов/минуту

Query Parameters:
  - cursor: string
  - limit: integer, default=50, min=1, max=200
  - user_id: string
  - action: string
  - resource_type: enum [project, workflow, config, agent, artifact]
  - resource_id: string
  - from: string, format=date-time
  - to: string, format=date-time
  - ip_address: string

Response 200:
  type: object
  properties:
    data: { type: array, items: { $ref: AuditLogEntry } }
    pagination: { $ref: Pagination }
```

#### GET /api/v1/admin/system/health

```yaml
Endpoint: GET /api/v1/admin/system/health
Summary: Health check системы
Authentication: Bearer Token (требуется, роль: admin)
Rate Limit: 60 запросов/минуту

Response 200:
  type: object
  properties:
    status: { type: string, enum: [healthy, degraded, unhealthy] }
    version: { type: string }
    uptime_seconds: { type: integer }
    timestamp: { type: string, format: date-time }
    components:
      type: object
      properties:
        api: { $ref: HealthStatus }
        database: { $ref: HealthStatus }
        redis: { $ref: HealthStatus }
        agent_pool: { $ref: HealthStatus }
        llm_providers: { $ref: HealthStatus }
        storage: { $ref: HealthStatus }
    metrics:
      type: object
      properties:
        active_workflows: { type: integer }
        queued_workflows: { type: integer }
        active_agents: { type: integer }
        requests_per_minute: { type: integer }
        average_response_time_ms: { type: integer }
        error_rate_percentage: { type: number }
```

---

**Продолжение в части 2: OpenAPI спецификация, схемы данных, обработка ошибок,
WebSocket API, webhooks, безопасность**
