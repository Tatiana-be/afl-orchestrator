# AFL Orchestrator: Документация API Парсера

**Версия**: 1.0 **Дата**: 2026-04-04 **Статус**: Draft **Задача**: PARSER-010

---

## 1. Обзор

Парсер AFL Orchestrator преобразует конфигурационные файлы (YAML/JSON) в
типизированную модель `AFLConfig` и выполняет комплексную валидацию перекрёстных
ссылок.

### 1.1 Компоненты

| Компонент   | Путь                                     | Описание                            |
| ----------- | ---------------------------------------- | ----------------------------------- |
| `AFLParser` | `src/orchestrator/parser/afl_parser.py`  | Основной парсер YAML/JSON           |
| `Schema`    | `src/orchestrator/parser/schema.py`      | Pydantic-модели конфигурации        |
| REST API    | `src/orchestrator/api/routes/configs.py` | HTTP-эндпоинты управления конфигами |

### 1.2 Базовый URL

```
/api/v1/projects/{project_id}/configs
```

---

## 2. YAML Anchors & Aliases (PARSER-003)

Парсер использует `yaml.FullLoader`, который поддерживает:

| Синтаксис      | Описание                                       | Пример           |
| -------------- | ---------------------------------------------- | ---------------- |
| `&name`        | Anchor — именованная ссылка                    | `type: &t "llm"` |
| `*name`        | Alias — разрешение ссылки                      | `type: *t`       |
| `<<: *name`    | Merge key — слияние объекта с переопределением | `<<: *defaults`  |
| `<<: [*a, *b]` | Множественное слияние (ограниченная поддержка) | —                |

### 2.1 Пример: базовый anchor + alias

```yaml
agents:
  - id: agent_a
    type: &agent_type "llm" # anchor
    model: "gpt-4"
  - id: agent_b
    type: *agent_type # alias → "llm"
    model: "claude-3"
```

### 2.2 Пример: merge key (`<<:`)

```yaml
agents:
  - &defaults
    id: agent_a
    type: llm
    tools:
      - file_read
    guardrails: []

  - <<: *defaults # merge с переопределением
    id: agent_b
    model: claude-3
    tools:
      - web_search
      - code_exec

  - <<: *defaults # merge без переопределений
    id: agent_c
```

**Результат парсинга:**

| Агент   | type | model    | tools                   |
| ------- | ---- | -------- | ----------------------- |
| agent_a | llm  | gpt-4    | [file_read]             |
| agent_b | llm  | claude-3 | [web_search, code_exec] |
| agent_c | llm  | gpt-4    | [file_read]             |

### 2.3 Валидация + Anchors

Merge-конфигурации проходят все проверки валидации (agent/artifact/guardrail
references, circular dependencies) наравне с обычными конфигами.

---

## 3. Circular Dependency Detection (PARSER-006)

Парсер обнаруживает циклические зависимости в графе workflow с помощью DFS
(Depth-First Search) с трёхцветной раскраской вершин.

### 3.1 Алгоритм

1. Построить граф зависимостей (adjacency list): `step → depends_on[]`
2. DFS с цветовой маркировкой:
   - **WHITE** — не посещён
   - **GRAY** — в обработке (в текущем пути)
   - **BLACK** — завершён
3. Если найден GRAY-сосед → обнаружен цикл
4. Отслеживать путь для формирования полного цикла

### 3.2 Примеры

**Прямой цикл (A → B → A):**

```yaml
workflow:
  - step: step_a
    agent: agent_a
    depends_on: [step_b]
  - step: step_b
    agent: agent_b
    depends_on: [step_a]
```

**Результат:**

```json
{
  "type": "circular_dependency",
  "field": "depends_on",
  "cycle": ["step_a", "step_b", "step_a"],
  "message": "Circular dependency detected: step_a -> step_b -> step_a"
}
```

**Косвенный цикл (A → B → C → A):**

```yaml
workflow:
  - step: a
    agent: agent_a
    depends_on: [c]
  - step: b
    agent: agent_a
    depends_on: [a]
  - step: c
    agent: agent_a
    depends_on: [b]
```

**Самозависимость:**

```yaml
workflow:
  - step: a
    agent: agent_a
    depends_on: [a]
```

**Валидный DAG (без циклов):**

```yaml
workflow:
  - step: a
    agent: agent_a
  - step: b
    agent: agent_a
    depends_on: [a]
  - step: c
    agent: agent_a
    depends_on: [a]
  - step: d
    agent: agent_a
    depends_on: [b, c]
```

### 3.3 Множественные циклы

Если в графе несколько независимых циклов — все будут обнаружены и отражены в
списке ошибок.

---

## 4. JSON Parsing (PARSER-004)

Парсер поддерживает JSON как альтернативный формат конфигурации. Используется
стандартный `json.loads()` с последующей валидацией через Pydantic.

| Аспект              | YAML                      | JSON                       |
| ------------------- | ------------------------- | -------------------------- |
| **Метод**           | `parse_yaml()`, `parse()` | `parse_json()`, `parse()`  |
| **Loader**          | `yaml.FullLoader`         | `json.loads()`             |
| **Anchors/Aliases** | ✅ Да (`&`, `*`, `<<:`)   | ❌ Нет (не поддерживается) |
| **Comments**        | ✅ Да                     | ❌ Нет                     |
| **Unicode**         | ✅ UTF-8                  | ✅ UTF-8                   |

### 3.1 Программный API

```python
from src.orchestrator.parser.afl_parser import AFLParser

parser = AFLParser()

# Прямой вызов
config = parser.parse_json(json_string)

# Через универсальный метод
config = parser.parse(json_string, format="json")
```

### 3.2 Пример: полный JSON-конфиг

```json
{
  "version": "1.0",
  "project": "Code Review Pipeline",
  "budget": {
    "total_tokens": 100000,
    "warning_threshold": 0.8,
    "hard_limit": 120000
  },
  "agents": [
    {
      "id": "reviewer",
      "type": "llm",
      "model": "gpt-4",
      "tools": ["file_read", "diff"],
      "guardrails": ["no_secrets"]
    }
  ],
  "artifacts": [
    { "id": "report", "type": "json", "path": "/output/review.json" }
  ],
  "guardrails": [{ "id": "no_secrets", "type": "regex", "action": "block" }],
  "workflow": [
    {
      "step": "review",
      "agent": "reviewer",
      "artifact": "report",
      "depends_on": []
    }
  ]
}
```

### 3.3 Ошибки парсинга

| Ошибка             | Исключение                 | Причина                 |
| ------------------ | -------------------------- | ----------------------- |
| Невалидный JSON    | `json.JSONDecodeError`     | Синтаксическая ошибка   |
| Schema mismatch    | `pydantic.ValidationError` | Неверные типы/поля      |
| Неизвестный формат | `ValueError`               | `format != "yaml/json"` |

```python
# Malformed JSON → JSONDecodeError
parser.parse_json('{"broken": }')

# Bad schema → ValidationError
parser.parse_json('{"version": "bad", "project": "Test", "agents": [], "workflow": []}')
# pydantic.ValidationError: version doesn't match pattern ^\d+\.\d+$
```

### 3.4 Unicode

JSON полностью поддерживает Unicode — кириллица, эмодзи, CJK:

```json
{
  "version": "1.0",
  "project": "Тест Юникод Проект 🚀",
  "agents": [{ "id": "агент_1", "type": "llm" }],
  "workflow": [{ "step": "анализ", "agent": "агент_1" }]
}
```

### 3.5 Когда использовать JSON vs YAML

| Критерий            | YAML | JSON |
| ------------------- | ---- | ---- |
| Человеко-читаемость | ✅   | ⚠️   |
| Комментарии         | ✅   | ❌   |
| Anchors/Merge keys  | ✅   | ❌   |
| Machine-generated   | ⚠️   | ✅   |
| Строгая типизация   | ⚠️   | ✅   |

**Рекомендация:** YAML для ручной настройки, JSON для программной генерации.

---

## 4. Схема Конфигурации (AFLConfig)

### 4.1 Корневая модель

```typescript
interface AFLConfig {
  version: string; // паттерн: ^\d+\.\d+$  (напр. "1.0")
  project: string; // название проекта
  budget?: BudgetConfig; // лимиты токенов и стоимости
  agents: AgentConfig[]; // пул агентов
  artifacts?: ArtifactConfig[]; // выходные артефакты
  guardrails?: GuardrailConfig[]; // правила валидации
  workflow: WorkflowStep[]; // пайплайн шагов
}
```

### 4.2 BudgetConfig

```typescript
interface BudgetConfig {
  total_tokens: number; // > 0
  warning_threshold: number; // 0.8, диапазон [0, 1]
  hard_limit?: number; // абсолютный лимит
}
```

### 4.3 AgentConfig

```typescript
interface AgentConfig {
  id: string; // уникальный идентификатор агента
  type: string; // тип агента: "llm", "script", "human"
  model?: string; // LLM-модель (для type="llm")
  tools: string[]; // доступные инструменты
  guardrails: string[]; // привязанные guardrail-правила (ссылки на GuardrailConfig.id)
}
```

### 4.4 ArtifactConfig

```typescript
interface ArtifactConfig {
  id: string; // уникальный идентификатор артефакта
  type: string; // тип: "file", "json", "text", "image", "code"
  url?: string; // URL артефакта
  path?: string; // файловый путь
}
```

### 4.5 GuardrailConfig

```typescript
interface GuardrailConfig {
  id: string; // уникальный идентификатор правила
  type: string; // тип: "regex", "llm_judge", "keyword", "custom"
  action: string; // действие при нарушении: "block" (по умолчанию), "flag", "modify"
}
```

### 4.6 WorkflowStep

```typescript
interface WorkflowStep {
  step: string; // идентификатор шага
  agent: string; // ссылка на AgentConfig.id
  depends_on: string[]; // ссылки на другие WorkflowStep.step
  artifact?: string; // ссылка на ArtifactConfig.id
}
```

---

## 5. REST API Эндпоинты

### 5.1 Загрузка конфига

```
POST /api/v1/projects/{project_id}/configs
```

**Описание:** Парсит и сохраняет новую версию AFL-конфигурации.

**Rate Limit:** 10 запросов/минуту

**Path Parameters:**

| Параметр     | Тип           | Обязательный | Описание              |
| ------------ | ------------- | ------------ | --------------------- |
| `project_id` | string (UUID) | ✅           | Идентификатор проекта |

**Request Body:**

```json
{
  "content": "string  (YAML или JSON, обязательно)",
  "format": "yaml | json (по умолчанию: yaml)",
  "version": "string (semver, автогенерация если не указан)",
  "changelog": "string (макс. 500 символов)"
}
```

**Response 201 Created:**

```json
{
  "config_id": "cfg_abc123",
  "project_id": "proj_xyz",
  "version": "1.2.0",
  "validation_status": "valid | invalid | warnings",
  "validation_errors": []
}
```

**Response 422 Unprocessable Entity** (ошибка парсинга):

```json
{
  "error": {
    "code": "PARSE_ERROR",
    "message": "Invalid YAML syntax at line 5, column 3",
    "details": { "line": 5, "column": 3 },
    "timestamp": "2026-04-04T10:30:00Z",
    "request_id": "req-abc123"
  }
}
```

**Пример запроса (YAML):**

```bash
curl -X POST https://api.afl-orchestrator.com/api/v1/projects/proj_xyz/configs \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "version: \"1.0\"\nproject: MyProject\nagents:\n  - id: agent_a\n    type: llm\n    model: gpt-4\nworkflow:\n  - step: analyze\n    agent: agent_a\n",
    "format": "yaml",
    "version": "1.0.0",
    "changelog": "Initial config"
  }'
```

**Пример запроса (JSON):**

```bash
curl -X POST https://api.afl-orchestrator.com/api/v1/projects/proj_xyz/configs \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "{\"version\":\"1.0\",\"project\":\"MyProject\",\"agents\":[{\"id\":\"agent_a\",\"type\":\"llm\",\"model\":\"gpt-4\"}],\"workflow\":[{\"step\":\"analyze\",\"agent\":\"agent_a\"}]}",
    "format": "json"
  }'
```

---

### 5.2 Валидация конфига (без сохранения)

```
POST /api/v1/projects/{project_id}/configs/validate
```

**Описание:** Парсит и валидирует AFL-конфигурацию без сохранения в БД.
Используется для превентивной проверки перед загрузкой.

**Rate Limit:** 20 запросов/минуту

**Path Parameters:**

| Параметр     | Тип           | Обязательный | Описание              |
| ------------ | ------------- | ------------ | --------------------- |
| `project_id` | string (UUID) | ✅           | Идентификатор проекта |

**Request Body:**

```json
{
  "content": "string  (YAML или JSON, обязательно)",
  "format": "yaml | json (по умолчанию: yaml)",
  "strict": "boolean (по умолчанию: false)"
}
```

**Response 200 OK:**

```json
{
  "valid": true,
  "status": "valid | invalid | warnings",
  "errors": [],
  "warnings": [],
  "parsed_config": {
    "version": "1.0",
    "project": "MyProject",
    "agents": [...],
    "workflow": [...]
  }
}
```

**Response 200 OK (с ошибками):**

```json
{
  "valid": false,
  "status": "invalid",
  "errors": [
    {
      "type": "invalid_reference",
      "field": "agent",
      "step": "analyze",
      "value": "nonexistent_agent",
      "message": "Step 'analyze' references unknown agent 'nonexistent_agent'"
    },
    {
      "type": "circular_dependency",
      "field": "depends_on",
      "cycle": ["step_a", "step_b", "step_a"],
      "message": "Circular dependency detected: step_a -> step_b -> step_a"
    }
  ],
  "warnings": [],
  "parsed_config": null
}
```

**Пример запроса:**

```bash
curl -X POST https://api.afl-orchestrator.com/api/v1/projects/proj_xyz/configs/validate \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "version: \"1.0\"\nproject: Test\nagents:\n  - id: a1\n    type: llm\nworkflow:\n  - step: s1\n    agent: ghost_agent\n",
    "format": "yaml",
    "strict": true
  }'
```

---

### 5.3 Список версий конфига

```
GET /api/v1/projects/{project_id}/configs
```

**Описание:** Возвращает список всех версий конфигурации проекта с пагинацией.

**Rate Limit:** 30 запросов/минуту

**Query Parameters:**

| Параметр | Тип     | Обязательный | По умолчанию | Описание                                 |
| -------- | ------- | ------------ | ------------ | ---------------------------------------- |
| `cursor` | string  | ❌           | —            | Курсор пагинации                         |
| `limit`  | integer | ❌           | 20           | Размер страницы (1–100)                  |
| `sort`   | string  | ❌           | created_at   | Поле сортировки: `created_at`, `version` |
| `order`  | string  | ❌           | desc         | Порядок: `asc`, `desc`                   |

**Response 200 OK:**

```json
{
  "data": [
    {
      "config_id": "cfg_abc123",
      "project_id": "proj_xyz",
      "version": "1.2.0",
      "created_at": "2026-04-04T10:30:00Z",
      "created_by": "user_123",
      "changelog": "Added guardrails",
      "validation_status": "valid"
    }
  ],
  "pagination": {
    "cursor": "eyJpZCI6MjB9",
    "next_cursor": "eyJpZCI6NDB9",
    "prev_cursor": null,
    "limit": 20,
    "has_more": true
  }
}
```

---

### 5.4 Получение конкретной версии

```
GET /api/v1/projects/{project_id}/configs/{version}
```

**Описание:** Возвращает полную конфигурацию указанной версии.

**Rate Limit:** 30 запросов/минуту

**Path Parameters:**

| Параметр     | Тип           | Обязательный | Описание                     |
| ------------ | ------------- | ------------ | ---------------------------- |
| `project_id` | string (UUID) | ✅           | Идентификатор проекта        |
| `version`    | string        | ✅           | Версия конфигурации (semver) |

**Response 200 OK:**

```json
{
  "config_id": "cfg_abc123",
  "project_id": "proj_xyz",
  "version": "1.2.0",
  "content": {
    "version": "1.0",
    "project": "MyProject",
    "budget": {
      "total_tokens": 100000,
      "warning_threshold": 0.8
    },
    "agents": [
      {
        "id": "agent_a",
        "type": "llm",
        "model": "gpt-4",
        "tools": ["file_read", "web_search"],
        "guardrails": ["guardrail_1"]
      }
    ],
    "artifacts": [
      {
        "id": "artifact_x",
        "type": "file"
      }
    ],
    "guardrails": [
      {
        "id": "guardrail_1",
        "type": "regex",
        "action": "block"
      }
    ],
    "workflow": [
      {
        "step": "analyze",
        "agent": "agent_a",
        "depends_on": [],
        "artifact": "artifact_x"
      }
    ]
  },
  "created_at": "2026-04-04T10:30:00Z",
  "created_by": "user_123",
  "changelog": "Added guardrails",
  "validation_status": "valid"
}
```

**Response 404 Not Found:**

```json
{
  "error": {
    "code": "CONFIG_NOT_FOUND",
    "message": "Config version '9.9.9' not found for project 'proj_xyz'",
    "timestamp": "2026-04-04T10:30:00Z",
    "request_id": "req-abc123"
  }
}
```

---

### 5.5 Последняя версия

```
GET /api/v1/projects/{project_id}/configs/latest
```

**Описание:** Возвращает последнюю загруженную версию конфигурации.

**Rate Limit:** 30 запросов/минуту

**Response 200 OK:** — та же структура, что и `GET /configs/{version}`

**Response 404 Not Found:**

```json
{
  "error": {
    "code": "NO_CONFIG_FOUND",
    "message": "No configurations exist for project 'proj_xyz'",
    "timestamp": "2026-04-04T10:30:00Z",
    "request_id": "req-abc123"
  }
}
```

---

### 5.6 Сравнение версий

```
GET /api/v1/projects/{project_id}/configs/{v1}/diff/{v2}
```

**Описание:** Построчное сравнение двух версий конфигурации.

**Rate Limit:** 10 запросов/минуту

**Path Parameters:**

| Параметр     | Тип           | Обязательный | Описание              |
| ------------ | ------------- | ------------ | --------------------- |
| `project_id` | string (UUID) | ✅           | Идентификатор проекта |
| `v1`         | string        | ✅           | Базовая версия        |
| `v2`         | string        | ✅           | Целевая версия        |

**Response 200 OK:**

```json
{
  "version_a": "1.0.0",
  "version_b": "1.2.0",
  "diff": {
    "added": ["agents[1] (agent_b)"],
    "removed": [],
    "modified": [
      {
        "path": "workflow[0].agent",
        "old_value": "agent_a",
        "new_value": "agent_b"
      }
    ]
  },
  "validation_changes": {
    "v1_errors": 0,
    "v2_errors": 0,
    "v1_warnings": 1,
    "v2_warnings": 0
  }
}
```

---

## 6. Программа API (Python)

### 6.1 AFLParser

Основной класс парсера. Доступен через
`from src.orchestrator.parser.afl_parser import AFLParser`.

#### parse_yaml(content: str) → AFLConfig

Парсит YAML-строку в объект `AFLConfig`.

```python
from src.orchestrator.parser.afl_parser import AFLParser

parser = AFLParser()
config = parser.parse_yaml("""
version: "1.0"
project: MyProject
agents:
  - id: agent_a
    type: llm
    model: gpt-4
workflow:
  - step: analyze
    agent: agent_a
""")

print(config.version)     # "1.0"
print(config.project)     # "MyProject"
print(config.agents[0].id) # "agent_a"
```

**Exceptions:**

| Исключение                 | Условие                              |
| -------------------------- | ------------------------------------ |
| `yaml.YAMLError`           | Неверный YAML-синтаксис              |
| `pydantic.ValidationError` | YAML распарсен, но не проходит схему |

#### parse_json(content: str) → AFLConfig

Парсит JSON-строку в объект `AFLConfig`.

```python
config = parser.parse_json("""
{
  "version": "1.0",
  "project": "MyProject",
  "agents": [{"id": "agent_a", "type": "llm", "model": "gpt-4"}],
  "workflow": [{"step": "analyze", "agent": "agent_a"}]
}
""")
```

**Exceptions:**

| Исключение                 | Условие                              |
| -------------------------- | ------------------------------------ |
| `json.JSONDecodeError`     | Неверный JSON-синтаксис              |
| `pydantic.ValidationError` | JSON распарсен, но не проходит схему |

#### parse(content: str, format: str = "yaml") → AFLConfig

Универсальный метод. Диспатчит на `parse_yaml` или `parse_json` в зависимости от
`format`.

```python
config = parser.parse(yaml_string, format="yaml")
config = parser.parse(json_string, format="json")
```

**Exceptions:**

| Исключение   | Условие                                                      |
| ------------ | ------------------------------------------------------------ |
| `ValueError` | Неизвестный формат (`format != "yaml" and format != "json"`) |

#### validate(config: AFLConfig) → list[dict[str, Any]]

Выполняет комплексную валидацию конфигурации. Возвращает список словарей с
ошибками. Пустой список означает валидную конфигурацию.

```python
errors = parser.validate(config)
if errors:
    for err in errors:
        print(f"[{err['type']}] {err['message']}")
else:
    print("Config is valid")
```

---

## 7. Типы Ошибок Валидации

### 7.1 invalid_reference

Неверная перекрёстная ссылка. Возникает когда workflow step ссылается на
несуществующий agent, artifact или depends_on шаг, либо когда agent ссылается на
несуществующий guardrail.

**Структура:**

```json
{
  "type": "invalid_reference",
  "field": "agent | artifact | guardrail | depends_on",
  "message": "Человекочитаемое описание",
  "value": "ссылочный_id"
}
```

**Дополнительные поля по context:**

| field        | Доп. поле | Пример                 |
| ------------ | --------- | ---------------------- |
| `agent`      | `step`    | `{"step": "analyze"}`  |
| `artifact`   | `step`    | `{"step": "review"}`   |
| `guardrail`  | `agent`   | `{"agent": "agent_a"}` |
| `depends_on` | `step`    | `{"step": "step_b"}`   |

**Примеры:**

```json
// Неизвестный агент
{
  "type": "invalid_reference",
  "field": "agent",
  "step": "analyze",
  "value": "ghost_agent",
  "message": "Step 'analyze' references unknown agent 'ghost_agent'"
}

// Неизвестный артефакт
{
  "type": "invalid_reference",
  "field": "artifact",
  "step": "review",
  "value": "nonexistent_artifact",
  "message": "Step 'review' references unknown artifact 'nonexistent_artifact'"
}

// Неизвестный guardrail
{
  "type": "invalid_reference",
  "field": "guardrail",
  "agent": "agent_a",
  "value": "ghost_guardrail",
  "message": "Agent 'agent_a' references unknown guardrail 'ghost_guardrail'"
}

// Неизвестная зависимость
{
  "type": "invalid_reference",
  "field": "depends_on",
  "step": "step_b",
  "value": "ghost_step",
  "message": "Step 'step_b' depends on unknown step 'ghost_step'"
}
```

### 7.2 circular_dependency

Циклическая зависимость в графе workflow. Обнаруживается через DFS.

**Структура:**

```json
{
  "type": "circular_dependency",
  "field": "depends_on",
  "cycle": ["step_a", "step_b", "step_c", "step_a"],
  "message": "Circular dependency detected: step_a -> step_b -> step_c -> step_a"
}
```

**Примеры:**

```json
// Прямой цикл: A -> B -> A
{
  "type": "circular_dependency",
  "field": "depends_on",
  "cycle": ["step_a", "step_b", "step_a"],
  "message": "Circular dependency detected: step_a -> step_b -> step_a"
}

// Косвенный цикл: A -> B -> C -> A
{
  "type": "circular_dependency",
  "field": "depends_on",
  "cycle": ["step_a", "step_b", "step_c", "step_a"],
  "message": "Circular dependency detected: step_a -> step_b -> step_c -> step_a"
}

// Самозависимость
{
  "type": "circular_dependency",
  "field": "depends_on",
  "cycle": ["step_a", "step_a"],
  "message": "Circular dependency detected: step_a -> step_a"
}
```

---

## 8. Валидация Схемы (Pydantic)

Помимо логической валидации (`validate()`), Pydantic автоматически проверяет
структурную целостность при парсинге.

### 8.1 Schema-Level Ошибки

| Поле                       | Ограничение          | Код ошибки                              |
| -------------------------- | -------------------- | --------------------------------------- |
| `version`                  | паттерн `^\d+\.\d+$` | `string_pattern_mismatch`               |
| `budget.total_tokens`      | `gt=0`               | `greater_than`                          |
| `budget.warning_threshold` | `ge=0, le=1`         | `greater_than_equal`, `less_than_equal` |
| `agent.id`                 | required             | `missing`                               |
| `agent.type`               | required             | `missing`                               |
| `workflow.step`            | required             | `missing`                               |
| `workflow.agent`           | required             | `missing`                               |

### 8.2 Пример Schema-Level Ошибки

```json
{
  "type": "value_error",
  "loc": ["budget", "total_tokens"],
  "msg": "Input should be greater than 0",
  "input": 0,
  "ctx": { "gt": 0 }
}
```

---

## 9. Полный Пример Workflow

### 9.1 YAML-конфигурация

```yaml
version: "1.0"
project: Code Review Pipeline
budget:
  total_tokens: 100000
  warning_threshold: 0.8
  hard_limit: 120000

agents:
  - id: reviewer
    type: llm
    model: gpt-4
    tools: [file_read, diff]
    guardrails: [no_secrets, no_pii]

  - id: summarizer
    type: llm
    model: claude-3
    guardrails: [no_secrets]

  - id: notifier
    type: script
    tools: [slack_notify]

artifacts:
  - id: review_report
    type: json
    path: /output/review.json

  - id: summary
    type: text
    path: /output/summary.txt

guardrails:
  - id: no_secrets
    type: regex
    action: block

  - id: no_pii
    type: llm_judge
    action: flag

workflow:
  - step: analyze_changes
    agent: reviewer
    artifact: review_report
    depends_on: []

  - step: generate_summary
    agent: summarizer
    artifact: summary
    depends_on: [analyze_changes]

  - step: notify_team
    agent: notifier
    depends_on: [generate_summary]
```

### 9.2 Валидация через API

```bash
# 1. Validate without saving
curl -X POST https://api.afl-orchestrator.com/api/v1/projects/proj_123/configs/validate \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"content": "'"$YAML_CONTENT"'", "format": "yaml"}'

# Response: {"valid": true, "status": "valid", "errors": [], "warnings": []}

# 2. Upload config
curl -X POST https://api.afl-orchestrator.com/api/v1/projects/proj_123/configs \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"content": "'"$YAML_CONTENT"'", "format": "yaml", "version": "1.0.0", "changelog": "Initial pipeline"}'

# Response: {"config_id": "cfg_abc", "project_id": "proj_123", "version": "1.0.0", "validation_status": "valid"}

# 3. Get latest config
curl -X GET https://api.afl-orchestrator.com/api/v1/projects/proj_123/configs/latest \
  -H "Authorization: Bearer $TOKEN"
```

### 9.3 Программная валидация

```python
from src.orchestrator.parser.afl_parser import AFLParser

parser = AFLParser()

# Parse YAML
config = parser.parse_yaml(yaml_content)

# Validate
errors = parser.validate(config)

if errors:
    # Categorize errors
    ref_errors = [e for e in errors if e["type"] == "invalid_reference"]
    cycle_errors = [e for e in errors if e["type"] == "circular_dependency"]

    print(f"Found {len(ref_errors)} invalid references and {len(cycle_errors)} cycles")

    for err in ref_errors:
        print(f"  [{err['field']}] {err['message']}")
    for err in cycle_errors:
        print(f"  Cycle: {' -> '.join(err['cycle'])}")
else:
    print("✓ Configuration is valid")
    print(f"  Agents: {len(config.agents)}")
    print(f"  Workflow steps: {len(config.workflow)}")
    print(f"  Artifacts: {len(config.artifacts or [])}")
    print(f"  Guardrails: {len(config.guardrails or [])}")
```

---

## 10. Таблица Всех Ошибок

| Тип                   | Причина                     | HTTP Status      |
| --------------------- | --------------------------- | ---------------- |
| `PARSE_ERROR`         | Ошибка синтаксиса YAML/JSON | 422              |
| `SCHEMA_ERROR`        | Pydantic validation         | 422              |
| `INVALID_REFERENCE`   | Битая ссылка                | 200 (в errors[]) |
| `CIRCULAR_DEPENDENCY` | Цикл в depends_on           | 200 (в errors[]) |
| `CONFIG_NOT_FOUND`    | Версия не найдена           | 404              |
| `NO_CONFIG_FOUND`     | Нет конфигов                | 404              |
| `DUPLICATE_VERSION`   | Повторная версия            | 409              |

---

## 11. Матрица Валидации

| Проверка              | Метод        | Когда          | Что                                                          |
| --------------------- | ------------ | -------------- | ------------------------------------------------------------ |
| YAML/JSON синтаксис   | `parse()`    | При парсинге   | Корректность формата                                         |
| Pydantic схема        | `parse()`    | При парсинге   | Типы, required-поля, ограничения                             |
| Agent references      | `validate()` | После парсинга | Все `workflow[].agent` существуют в `agents[]`               |
| Artifact references   | `validate()` | После парсинга | Все `workflow[].artifact` существуют в `artifacts[]`         |
| Guardrail references  | `validate()` | После парсинга | Все `agents[].guardrails[]` существуют в `guardrails[]`      |
| Dependency references | `validate()` | После парсинга | Все `workflow[].depends_on[]` существуют в `workflow[].step` |
| Circular dependencies | `validate()` | После парсинга | Нет циклов в графе depends_on                                |

---

## 12. Changelog

| Версия | Дата       | Изменение                          |
| ------ | ---------- | ---------------------------------- |
| 1.0    | 2026-04-04 | Initial documentation (PARSER-010) |
