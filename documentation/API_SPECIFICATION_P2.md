# AFL Orchestrator: Спецификация API (Часть 2)

**OpenAPI, Схемы Данных, Обработка Ошибок, WebSocket, Webhooks, Безопасность**

---

## 3. OpenAPI 3.0 Спецификация (фрагмент)

```yaml
openapi: 3.0.3
info:
  title: AFL Orchestrator API
  description: |
    API для управления мульти-агентными AI-пайплайнами.

    ## Аутентификация
    Bearer Token в header `Authorization`.

    ## Rate Limiting
    - Free: 30 req/min
    - Pro: 100 req/min
    - Enterprise: 500 req/min
  version: 1.0.0
  contact:
    name: API Support
    email: api-support@afl-orchestrator.com

servers:
  - url: https://api.afl-orchestrator.com/api/v1
    description: Production
  - url: https://staging-api.afl-orchestrator.com/api/v1
    description: Staging
  - url: https://dev-api.afl-orchestrator.local/api/v1
    description: Development

tags:
  - name: Projects
  - name: Configs
  - name: Workflows
  - name: Agents
  - name: Artifacts
  - name: Budget
  - name: Events
  - name: Admin

security:
  - BearerAuth: []

paths:
  /projects:
    post:
      tags: [Projects]
      summary: Создание проекта
      operationId: createProject
      requestBody:
        required: true
        content:
          application/json:
            schema: { $ref: "#/components/schemas/CreateProjectRequest" }
      responses:
        "201":
          description: Created
          content:
            application/json:
              schema: { $ref: "#/components/schemas/Project" }
        "400":
          description: Bad Request
          content:
            application/json:
              schema: { $ref: "#/components/schemas/Error" }
        "401": { description: Unauthorized }
        "409": { description: Conflict }

    get:
      tags: [Projects]
      summary: Список проектов
      operationId: listProjects
      parameters:
        - { $ref: "#/components/parameters/CursorParam" }
        - { $ref: "#/components/parameters/LimitParam" }
        - name: status
          in: query
          schema:
            { type: string, enum: [active, archived, all], default: active }
      responses:
        "200":
          description: OK
          content:
            application/json:
              schema:
                type: object
                properties:
                  data:
                    {
                      type: array,
                      items: { $ref: "#/components/schemas/ProjectSummary" },
                    }
                  pagination: { $ref: "#/components/schemas/Pagination" }

  /workflows:
    post:
      tags: [Workflows]
      summary: Запуск workflow
      operationId: createWorkflow
      requestBody:
        required: true
        content:
          application/json:
            schema: { $ref: "#/components/schemas/CreateWorkflowRequest" }
      responses:
        "202":
          description: Accepted
          content:
            application/json:
              schema: { $ref: "#/components/schemas/WorkflowAccepted" }
        "400": { description: Bad Request }
        "403": { description: Forbidden }

    get:
      tags: [Workflows]
      summary: Список workflow
      operationId: listWorkflows
      parameters:
        - { $ref: "#/components/parameters/CursorParam" }
        - { $ref: "#/components/parameters/LimitParam" }
        - name: project_id
          in: query
          schema: { type: string }
        - name: status
          in: query
          schema:
            {
              type: string,
              enum: [queued, running, paused, completed, failed, cancelled],
            }
      responses:
        "200":
          description: OK
          content:
            application/json:
              schema:
                type: object
                properties:
                  data:
                    {
                      type: array,
                      items: { $ref: "#/components/schemas/WorkflowSummary" },
                    }
                  pagination: { $ref: "#/components/schemas/Pagination" }

  /workflows/{id}:
    get:
      tags: [Workflows]
      summary: Детали workflow
      operationId: getWorkflow
      parameters:
        - name: id
          in: path
          required: true
          schema: { type: string }
      responses:
        "200":
          description: OK
          content:
            application/json:
              schema: { $ref: "#/components/schemas/Workflow" }
        "404": { description: Not Found }

    delete:
      tags: [Workflows]
      summary: Отмена workflow
      operationId: cancelWorkflow
      parameters:
        - name: id
          in: path
          required: true
          schema: { type: string }
      responses:
        "204": { description: No Content }
        "400": { description: Bad Request }
        "404": { description: Not Found }

  /agents:
    get:
      tags: [Agents]
      summary: Список агентов
      operationId: listAgents
      parameters:
        - { $ref: "#/components/parameters/CursorParam" }
        - { $ref: "#/components/parameters/LimitParam" }
        - name: status
          in: query
          schema: { type: string, enum: [idle, busy, error, offline] }
      responses:
        "200":
          description: OK
          content:
            application/json:
              schema:
                type: object
                properties:
                  data:
                    {
                      type: array,
                      items: { $ref: "#/components/schemas/Agent" },
                    }
                  pagination: { $ref: "#/components/schemas/Pagination" }
                  summary: { $ref: "#/components/schemas/AgentPoolSummary" }

  /budget/alerts:
    post:
      tags: [Budget]
      summary: Создание алерта
      operationId: createBudgetAlert
      requestBody:
        required: true
        content:
          application/json:
            schema: { $ref: "#/components/schemas/CreateBudgetAlertRequest" }
      responses:
        "201":
          description: Created
          content:
            application/json:
              schema: { $ref: "#/components/schemas/BudgetAlert" }

  /webhooks:
    post:
      tags: [Events]
      summary: Создание webhook
      operationId: createWebhook
      requestBody:
        required: true
        content:
          application/json:
            schema: { $ref: "#/components/schemas/CreateWebhookRequest" }
      responses:
        "201":
          description: Created
          content:
            application/json:
              schema: { $ref: "#/components/schemas/Webhook" }

  /admin/audit-logs:
    get:
      tags: [Admin]
      summary: Аудит действий
      operationId: listAuditLogs
      security:
        - BearerAuth: []
      parameters:
        - { $ref: "#/components/parameters/CursorParam" }
        - { $ref: "#/components/parameters/LimitParam" }
        - name: user_id
          in: query
          schema: { type: string }
      responses:
        "200":
          description: OK
          content:
            application/json:
              schema:
                type: object
                properties:
                  data:
                    {
                      type: array,
                      items: { $ref: "#/components/schemas/AuditLogEntry" },
                    }
                  pagination: { $ref: "#/components/schemas/Pagination" }

  /admin/system/health:
    get:
      tags: [Admin]
      summary: Health check
      operationId: getSystemHealth
      responses:
        "200":
          description: OK
          content:
            application/json:
              schema: { $ref: "#/components/schemas/SystemHealth" }

components:
  securitySchemes:
    BearerAuth:
      type: http
      scheme: bearer
      bearerFormat: JWT

  parameters:
    CursorParam:
      name: cursor
      in: query
      schema: { type: string }
    LimitParam:
      name: limit
      in: query
      schema: { type: integer, default: 20, min: 1, max: 100 }

  schemas:
    Error:
      type: object
      properties:
        error:
          type: object
          properties:
            code: { type: string }
            message: { type: string }
            details: { type: object }
            timestamp: { type: string, format: date-time }
            request_id: { type: string }
            documentation_url: { type: string, format: uri }

    Pagination:
      type: object
      properties:
        cursor: { type: string }
        next_cursor: { type: string }
        prev_cursor: { type: string }
        limit: { type: integer }
        has_more: { type: boolean }

    Project:
      type: object
      properties:
        project_id: { type: string, format: uuid }
        name: { type: string }
        description: { type: string }
        created_at: { type: string, format: date-time }
        updated_at: { type: string, format: date-time }
        created_by: { type: string }
        status: { type: string, enum: [active, archived] }
        settings: { $ref: "#/components/schemas/ProjectSettings" }
        budget: { $ref: "#/components/schemas/ProjectBudget" }

    ProjectSummary:
      type: object
      properties:
        project_id: { type: string }
        name: { type: string }
        status: { type: string }
        created_at: { type: string, format: date-time }
        workflow_count: { type: integer }
        total_tokens_used: { type: integer }

    CreateProjectRequest:
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

    Workflow:
      type: object
      properties:
        workflow_id: { type: string }
        project_id: { type: string }
        config_version: { type: string }
        status:
          {
            type: string,
            enum: [queued, running, paused, completed, failed, cancelled],
          }
        progress: { type: number, min: 0, max: 1 }
        current_step: { type: string, nullable: true }
        total_steps: { type: integer }
        completed_steps: { type: integer }
        created_at: { type: string, format: date-time }
        started_at: { type: string, format: date-time, nullable: true }
        finished_at: { type: string, format: date-time, nullable: true }
        tokens_used: { type: integer }
        cost_usd: { type: number }
        steps:
          { type: array, items: { $ref: "#/components/schemas/WorkflowStep" } }
        artifacts:
          {
            type: array,
            items: { $ref: "#/components/schemas/ArtifactSummary" },
          }
        errors:
          { type: array, items: { $ref: "#/components/schemas/WorkflowError" } }

    WorkflowSummary:
      type: object
      properties:
        workflow_id: { type: string }
        project_id: { type: string }
        status: { type: string }
        progress: { type: number }
        current_step: { type: string, nullable: true }
        created_at: { type: string, format: date-time }
        tokens_used: { type: integer }

    CreateWorkflowRequest:
      type: object
      required: [project_id, config_version]
      properties:
        project_id: { type: string }
        config_version: { type: string }
        parameters: { type: object }
        priority:
          { type: string, enum: [low, normal, high, critical], default: normal }
        webhook_url: { type: string, format: uri }
        metadata: { type: object }

    WorkflowAccepted:
      type: object
      properties:
        workflow_id: { type: string }
        project_id: { type: string }
        status: { type: string, enum: [queued, pending] }
        created_at: { type: string, format: date-time }
        estimated_duration: { type: integer }
        status_url: { type: string, format: uri }

    WorkflowStep:
      type: object
      properties:
        step_id: { type: string }
        name: { type: string }
        status:
          { type: string, enum: [pending, running, completed, failed, skipped] }
        agent_id: { type: string }
        started_at: { type: string, format: date-time, nullable: true }
        completed_at: { type: string, format: date-time, nullable: true }
        tokens_used: { type: integer }
        retry_count: { type: integer }

    WorkflowError:
      type: object
      properties:
        step_id: { type: string }
        code: { type: string }
        message: { type: string }
        timestamp: { type: string, format: date-time }
        recoverable: { type: boolean }

    ArtifactSummary:
      type: object
      properties:
        artifact_id: { type: string }
        name: { type: string }
        type: { type: string }
        size_bytes: { type: integer }
        created_at: { type: string, format: date-time }
        download_url: { type: string, format: uri }

    Agent:
      type: object
      properties:
        agent_id: { type: string }
        name: { type: string }
        type: { type: string }
        model: { type: string }
        status: { type: string, enum: [idle, busy, error, offline] }
        current_workflow: { type: string, nullable: true }
        current_step: { type: string, nullable: true }
        created_at: { type: string, format: date-time }
        last_active: { type: string, format: date-time }
        tasks_completed: { type: integer }
        tokens_used_total: { type: integer }
        error_count: { type: integer }

    AgentPoolSummary:
      type: object
      properties:
        total: { type: integer }
        idle: { type: integer }
        busy: { type: integer }
        error: { type: integer }
        offline: { type: integer }

    BudgetAlert:
      type: object
      properties:
        alert_id: { type: string }
        project_id: { type: string }
        alert_type: { type: string, enum: [percentage, absolute, forecast] }
        threshold: { type: number }
        enabled: { type: boolean }
        created_at: { type: string, format: date-time }

    CreateBudgetAlertRequest:
      type: object
      required: [project_id, alert_type, threshold, notification_channels]
      properties:
        project_id: { type: string }
        alert_type: { type: string, enum: [percentage, absolute, forecast] }
        threshold: { type: number }
        notification_channels:
          {
            type: array,
            items: { type: string, enum: [email, slack, webhook] },
          }
        webhook_url: { type: string, format: uri }
        enabled: { type: boolean, default: true }

    Webhook:
      type: object
      properties:
        webhook_id: { type: string }
        project_id: { type: string }
        url: { type: string, format: uri }
        events: { type: array, items: { type: string } }
        active: { type: boolean }
        created_at: { type: string, format: date-time }

    CreateWebhookRequest:
      type: object
      required: [project_id, url, events, secret]
      properties:
        project_id: { type: string }
        url: { type: string, format: uri }
        events: { type: array, items: { type: string } }
        secret: { type: string, minLength: 16 }
        active: { type: boolean, default: true }
        headers: { type: object }
        retry_policy:
          type: object
          properties:
            max_retries: { type: integer, default: 3 }
            backoff_seconds: { type: integer, default: 60 }

    AuditLogEntry:
      type: object
      properties:
        log_id: { type: string }
        timestamp: { type: string, format: date-time }
        user_id: { type: string }
        user_email: { type: string }
        action: { type: string }
        resource_type: { type: string }
        resource_id: { type: string }
        ip_address: { type: string }
        status: { type: string, enum: [success, failure, forbidden] }
        details: { type: object }

    SystemHealth:
      type: object
      properties:
        status: { type: string, enum: [healthy, degraded, unhealthy] }
        version: { type: string }
        uptime_seconds: { type: integer }
        timestamp: { type: string, format: date-time }
        components: { type: object }
        metrics: { type: object }

    HealthStatus:
      type: object
      properties:
        status: { type: string, enum: [healthy, degraded, unhealthy] }
        latency_ms: { type: integer }
        last_check: { type: string, format: date-time }

    ProjectSettings:
      type: object
      properties:
        default_agent: { type: string }
        timezone: { type: string }
        allowed_integrations: { type: array, items: { type: string } }

    ProjectBudget:
      type: object
      properties:
        total_tokens: { type: integer }
        used_tokens: { type: integer }
        remaining_tokens: { type: integer }
        usage_percentage: { type: number }
        warning_threshold: { type: number }
        hard_limit: { type: integer }
```

---

## 4. Схемы Данных (Data Schemas)

### 4.1 Project

```typescript
interface Project {
  project_id: string; // UUID v4
  name: string; // 1-100 символов
  description?: string; // 0-500 символов
  created_at: string; // ISO 8601
  updated_at: string; // ISO 8601
  created_by: string; // User ID
  status: "active" | "archived";
  settings: ProjectSettings;
  budget: ProjectBudget;
  stats?: ProjectStats;
}

interface ProjectSettings {
  default_agent: string; // Модель по умолчанию
  timezone: string; // IANA timezone
  allowed_integrations: string[];
  custom_fields?: Record<string, any>;
}

interface ProjectBudget {
  total_tokens: number;
  used_tokens: number;
  remaining_tokens: number;
  warning_threshold: number; // 0.0-1.0
  hard_limit: number;
}

interface ProjectStats {
  total_workflows: number;
  active_workflows: number;
  completed_workflows: number;
  failed_workflows: number;
  total_agents_executed: number;
  average_workflow_duration: number;
}
```

### 4.2 Workflow

```typescript
type WorkflowStatus =
  | "queued"
  | "running"
  | "paused"
  | "completed"
  | "failed"
  | "cancelled";

type StepStatus = "pending" | "running" | "completed" | "failed" | "skipped";

interface Workflow {
  workflow_id: string;
  project_id: string;
  config_version: string;
  status: WorkflowStatus;
  progress: number; // 0.0-1.0
  current_step?: string;
  total_steps: number;
  completed_steps: number;
  failed_steps: number;
  created_at: string;
  started_at?: string;
  updated_at: string;
  finished_at?: string;
  estimated_duration: number;
  elapsed_time: number;
  tokens_used: number;
  cost_usd: number;
  parameters?: Record<string, any>;
  metadata?: Record<string, any>;
  steps: WorkflowStep[];
  artifacts: ArtifactSummary[];
  errors: WorkflowError[];
}

interface WorkflowStep {
  step_id: string;
  name: string;
  status: StepStatus;
  agent_id: string;
  agent_type: string;
  started_at?: string;
  completed_at?: string;
  tokens_used: number;
  retry_count: number;
  error?: StepError;
}

interface StepError {
  code: string;
  message: string;
  timestamp: string;
}

interface WorkflowError {
  step_id?: string;
  code: string;
  message: string;
  timestamp: string;
  recoverable: boolean;
}
```

### 4.3 Agent

```typescript
type AgentType = "llm" | "tool" | "hybrid" | "custom";

type AgentStatus = "idle" | "busy" | "error" | "offline";

interface Agent {
  agent_id: string;
  name: string;
  type: AgentType;
  model: string;
  status: AgentStatus;
  config: AgentConfig;
  current_task?: CurrentTask;
  metrics: AgentMetrics;
  capabilities: string[];
  tools: string[];
  created_at: string;
  last_active: string;
  health: AgentHealth;
}

interface AgentConfig {
  temperature: number; // 0.0-2.0
  max_tokens: number;
  timeout_seconds: number;
  retry_count: number;
  fallback_models?: string[];
}

interface CurrentTask {
  workflow_id: string;
  step_id: string;
  step_name: string;
  started_at: string;
  progress: number; // 0.0-1.0
}

interface AgentMetrics {
  tasks_completed: number;
  tasks_failed: number;
  tokens_used_total: number;
  tokens_used_today: number;
  average_task_duration: number;
  success_rate: number; // 0.0-1.0
}

interface AgentHealth {
  status: "healthy" | "degraded" | "unhealthy";
  last_check: string;
  cpu_usage: number; // 0.0-1.0
  memory_usage: number; // 0.0-1.0
  error_rate_1h: number; // 0.0-1.0
}
```

### 4.4 Artifact

```typescript
type ArtifactType =
  | "file"
  | "directory"
  | "json"
  | "text"
  | "image"
  | "archive";

interface Artifact {
  artifact_id: string;
  workflow_id: string;
  step_id: string;
  name: string;
  type: ArtifactType;
  storage_path: string; // S3 path
  size_bytes: number;
  mime_type: string;
  created_at: string;
  created_by: string; // Agent ID
  version: number;
  checksum: string; // SHA256
  metadata?: Record<string, any>;
  permissions: ArtifactPermissions;
}

interface ArtifactPermissions {
  owner: string;
  project_access: boolean;
  public: boolean;
  allowed_users: string[];
}
```

### 4.5 Event

```typescript
type EventType =
  // Workflow
  | "workflow.started"
  | "workflow.progress"
  | "workflow.step_completed"
  | "workflow.step_failed"
  | "workflow.step_retrying"
  | "workflow.completed"
  | "workflow.failed"
  | "workflow.paused"
  | "workflow.resumed"
  | "workflow.cancelled"
  // Budget
  | "budget.warning"
  | "budget.exceeded"
  | "budget.updated"
  // Agent
  | "agent.created"
  | "agent.destroyed"
  | "agent.error"
  | "agent.idle"
  | "agent.busy"
  // Config
  | "config.created"
  | "config.updated"
  | "config.validated"
  // Security
  | "guardrail.violation"
  | "auth.login"
  | "auth.logout"
  | "auth.failed";

interface Event {
  id: string;
  type: EventType;
  created_at: string;
  data: Record<string, any>;
  source: string;
  correlation_id?: string;
}
```

### 4.6 User

```typescript
type UserRole = "admin" | "developer" | "viewer" | "service";

type Permission =
  | "project:create"
  | "project:read"
  | "project:update"
  | "project:delete"
  | "workflow:create"
  | "workflow:read"
  | "workflow:update"
  | "workflow:cancel"
  | "config:create"
  | "config:read"
  | "config:update"
  | "admin:read"
  | "admin:write";

interface User {
  user_id: string;
  email: string;
  name: string;
  role: UserRole;
  created_at: string;
  last_login: string;
  permissions: Permission[];
  projects: ProjectMembership[];
}

interface ProjectMembership {
  project_id: string;
  role: "owner" | "admin" | "member" | "viewer";
  granted_at: string;
  granted_by: string;
}
```

### 4.7 AuditLog

```typescript
interface AuditLogEntry {
  log_id: string;
  timestamp: string;
  user_id: string;
  user_email: string;
  action: string; // "resource.operation"
  resource_type: string;
  resource_id: string;
  ip_address: string;
  user_agent: string;
  details: Record<string, any>;
  status: "success" | "failure" | "forbidden";
  error_code?: string;
  request_id: string;
}
```

---

## 5. Обработка Ошибок

### 5.1 Формат ошибок

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Человекочитаемое описание",
    "details": { "field": "value" },
    "timestamp": "2026-03-31T10:30:00Z",
    "request_id": "req-abc123",
    "documentation_url": "https://docs.afl-orchestrator.com/errors/ERROR_CODE"
  }
}
```

### 5.2 Коды ошибок

| Код                        | HTTP | Описание                  | Обработка                              |
| -------------------------- | ---- | ------------------------- | -------------------------------------- |
| `VALIDATION_ERROR`         | 400  | Ошибка валидации полей    | Проверить `details.errors`             |
| `PROJECT_NOT_FOUND`        | 404  | Проект не найден          | Проверить ID проекта                   |
| `PROJECT_NAME_EXISTS`      | 409  | Имя проекта занято        | Использовать другое имя                |
| `WORKFLOW_NOT_FOUND`       | 404  | Workflow не найден        | Проверить ID workflow                  |
| `WORKFLOW_CANNOT_PAUSE`    | 400  | Нельзя приостановить      | Проверить статус workflow              |
| `WORKFLOW_CANNOT_CANCEL`   | 400  | Нельзя отменить           | Проверить статус workflow              |
| `CONFIG_VALIDATION_ERROR`  | 400  | Ошибка валидации конфига  | Исправить YAML/JSON                    |
| `CONFIG_VERSION_EXISTS`    | 409  | Версия конфига существует | Использовать другую версию             |
| `BUDGET_EXCEEDED`          | 403  | Превышен бюджет           | Увеличить лимит или завершить workflow |
| `AGENT_NOT_FOUND`          | 404  | Агент не найден           | Проверить ID агента                    |
| `ARTIFACT_NOT_FOUND`       | 404  | Артефакт не найден        | Проверить ID артефакта                 |
| `ARTIFACT_ACCESS_DENIED`   | 403  | Нет доступа к артефакту   | Запросить доступ                       |
| `WEBHOOK_URL_EXISTS`       | 409  | Webhook URL существует    | Использовать другой URL                |
| `WEBHOOK_INACTIVE`         | 400  | Webhook не активен        | Активировать webhook                   |
| `INSUFFICIENT_PERMISSIONS` | 403  | Недостаточно прав         | Запросить роль admin                   |
| `VERSION_CONFLICT`         | 409  | Конфликт версий           | Перечитать и повторить                 |
| `DUPLICATE_WORKFLOW`       | 409  | Дубликат workflow         | Использовать другой ID                 |
| `RATE_LIMIT_EXCEEDED`      | 429  | Превышен лимит            | Ждать `Retry-After`                    |
| `UNAUTHORIZED`             | 401  | Неверный токен            | Обновить токен                         |
| `INTERNAL_ERROR`           | 500  | Внутренняя ошибка         | Повторить позже                        |
| `SERVICE_UNAVAILABLE`      | 503  | Сервис недоступен         | Проверить статус системы               |

### 5.3 Рекомендации по обработке

```typescript
// Пример обработки ошибок в клиенте
async function handleApiError(error: ApiError): Promise<void> {
  switch (error.code) {
    case "VALIDATION_ERROR":
      // Показать ошибки валидации в форме
      displayValidationErrors(error.details.errors);
      break;

    case "RATE_LIMIT_EXCEEDED":
      // Ждать указанное время и повторить
      const retryAfter = parseInt(error.headers["Retry-After"] || "60");
      await sleep(retryAfter * 1000);
      return retry();

    case "VERSION_CONFLICT":
      // Перечитать ресурс и повторить
      const latest = await fetchResource(error.details.resource_id);
      return updateResource(latest.id, mergeChanges(latest, pendingChanges));

    case "BUDGET_EXCEEDED":
      // Уведомить пользователя
      notifyUser("Бюджет превышен. Обратитесь к администратору.");
      break;

    case "UNAUTHORIZED":
      // Обновить токен
      await refreshToken();
      return retry();

    default:
      // Логировать и показать общее сообщение
      logError(error);
      showError("Произошла ошибка. Попробуйте позже.");
  }
}
```

---

## 6. WebSocket API (Real-time События)

### 6.1 Подключение

```
URL: wss://api.afl-orchestrator.com/api/v1/ws
Authentication: Bearer Token в query param или subprotocol
```

### 6.2 Формат сообщений

**Клиент → Сервер:**

```json
{
  "type": "subscribe",
  "channels": ["workflow:wf-123", "budget:proj-456"],
  "id": "msg-001"
}
```

**Сервер → Клиент:**

```json
{
  "type": "event",
  "channel": "workflow:wf-123",
  "event": "workflow.step_completed",
  "data": {
    "workflow_id": "wf-123",
    "step_id": "step-2",
    "step_name": "analyze_code",
    "completed_at": "2026-03-31T10:32:00Z",
    "tokens_used": 15000
  },
  "timestamp": "2026-03-31T10:32:00Z"
}
```

### 6.3 Типы сообщений

| Тип           | Направление     | Описание           |
| ------------- | --------------- | ------------------ |
| `subscribe`   | Client → Server | Подписка на каналы |
| `unsubscribe` | Client → Server | Отписка от каналов |
| `ping`        | Client → Server | Keep-alive         |
| `pong`        | Server → Client | Keep-alive ответ   |
| `event`       | Server → Client | Событие            |
| `error`       | Server → Client | Ошибка подписки    |

### 6.4 Каналы событий

| Канал           | События                  | Пример             |
| --------------- | ------------------------ | ------------------ |
| `workflow:{id}` | workflow.\*              | `workflow:wf-123`  |
| `project:{id}`  | config._, budget._       | `project:proj-456` |
| `agent:{id}`    | agent.\*                 | `agent:agent-789`  |
| `user:{id}`     | Все события пользователя | `user:user-001`    |

### 6.5 Reconnect логика

```typescript
class WebSocketClient {
  private reconnectDelay = 1000;
  private maxReconnectDelay = 30000;

  connect() {
    this.ws = new WebSocket(this.url);

    this.ws.onclose = () => {
      setTimeout(() => {
        this.reconnectDelay = Math.min(
          this.reconnectDelay * 1.5,
          this.maxReconnectDelay,
        );
        this.connect();
      }, this.reconnectDelay);
    };

    this.ws.onopen = () => {
      this.reconnectDelay = 1000;
      this.resubscribe();
    };
  }
}
```

---

## 7. Webhooks (Внешние Уведомления)

### 7.1 Формат Payload

```json
{
  "id": "evt-abc123",
  "type": "workflow.completed",
  "created_at": "2026-03-31T10:35:00Z",
  "data": {
    "workflow_id": "wf-123",
    "project_id": "proj-456",
    "completed_at": "2026-03-31T10:35:00Z",
    "duration_seconds": 300,
    "tokens_used": 45000,
    "cost_usd": 0.675
  },
  "metadata": {
    "attempt": 1,
    "webhook_id": "wh-789"
  }
}
```

### 7.2 Signature для верификации

**Headers:**

```
X-Webhook-Signature: sha256=abc123...
X-Webhook-Timestamp: 2026-03-31T10:35:00Z
X-Webhook-ID: evt-abc123
```

**Верификация (Python):**

```python
import hmac
import hashlib

def verify_webhook(payload: bytes, signature: str, secret: str) -> bool:
    expected = hmac.new(
        secret.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(f"sha256={expected}", signature)
```

### 7.3 Retry логика

| Attempt | Delay | Cumulative |
| ------- | ----- | ---------- |
| 1       | 0s    | 0s         |
| 2       | 60s   | 1m         |
| 3       | 300s  | 6m         |
| 4       | 900s  | 21m        |
| 5       | 2700s | 66m        |

**Max retries:** 5 **Max age:** 24 часа

---

## 8. Безопасность API

### 8.1 Аутентификация

**JWT Token:**

```json
{
  "sub": "user-123",
  "email": "user@example.com",
  "role": "developer",
  "permissions": ["project:read", "workflow:create"],
  "iat": 1680264000,
  "exp": 1680267600
}
```

**Refresh Token:**

- Срок жизни: 7 дней
- Хранение: HttpOnly cookie
- Rotation: при каждом использовании

### 8.2 Авторизация (Роли)

| Роль          | Права                             |
| ------------- | --------------------------------- |
| **admin**     | Полный доступ ко всем ресурсам    |
| **developer** | CRUD проектов, workflow, конфигов |
| **viewer**    | Только чтение                     |
| **service**   | Доступ по API key для сервисов    |

### 8.3 Rate Limiting

**Алгоритм:** Token Bucket **Ключи:** User ID, IP, API Key

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@app.post("/api/v1/workflows")
@limiter.limit("10/minute")
async def create_workflow(request: Request):
    ...
```

### 8.4 CORS Настройки

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://app.afl-orchestrator.com",
        "https://admin.afl-orchestrator.com"
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type", "Idempotency-Key"],
)
```

### 8.5 Input Validation

```python
from pydantic import BaseModel, validator, Field
import re

class CreateProjectRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: str = Field(None, max_length=500)

    @validator('name')
    def validate_name(cls, v):
        if not re.match(r'^[\w\s\-]+$', v):
            raise ValueError('Name contains invalid characters')
        if re.search(r'<script>', v, re.IGNORECASE):
            raise ValueError('XSS detected')
        return v
```

---

## 9. Версионирование и Совместимость

### 9.1 Стратегия версионирования

**URL Path:** `/api/v1/`, `/api/v2/`

**Deprecation политика:**

1. Объявление deprecation за 3 месяца
2. Поддержка минимум 2 версий одновременно
3. Sunset header в ответах

```
Sunset: Sat, 31 Dec 2026 23:59:59 GMT
Deprecation: true
Link: <https://api.afl-orchestrator.com/api/v2>; rel="successor-version"
```

### 9.2 Migration Guide v1 → v2

```markdown
## Breaking Changes в v2

### Projects

- `project_id` переименован в `id`
- `default_budget` теперь объект `BudgetConfig`

### Workflows

- Новый обязательный параметр `priority`
- `status` добавлены значения `queued`, `cancelled`

### Response Format

- Все списки теперь в поле `data`
- Добавлена пагинация `pagination`
```

### 9.3 Header для версии

```
Accept: application/vnd.afl.v1+json
Accept-Version: v1
```

---

## 10. Тестирование API

### 10.1 Postman Collection

```json
{
  "info": {
    "name": "AFL Orchestrator API",
    "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
  },
  "auth": {
    "type": "bearer",
    "bearer": [{ "key": "token", "value": "{{jwt_token}}" }]
  },
  "variable": [
    { "key": "base_url", "value": "https://api.afl-orchestrator.com/api/v1" }
  ],
  "item": [
    {
      "name": "Projects",
      "item": [
        {
          "name": "Create Project",
          "request": {
            "method": "POST",
            "header": [{ "key": "Content-Type", "value": "application/json" }],
            "body": { "mode": "raw", "raw": "{ \"name\": \"Test Project\" }" },
            "url": { "raw": "{{base_url}}/projects" }
          }
        }
      ]
    }
  ]
}
```

### 10.2 OpenAPI Validation

```bash
# Валидация спецификации
npx @redocly/cli lint openapi.yaml

# Тесты на соответствие
npx @redocly/cli bundle openapi.yaml

# Генерация клиентов
openapi-generator generate -i openapi.yaml -g typescript-axios -o ./client
```

### 10.3 Integration Tests

```python
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_create_workflow():
    async with AsyncClient() as client:
        response = await client.post(
            "http://testserver/api/v1/workflows",
            json={"project_id": "proj-123", "config_version": "1.0.0"},
            headers={"Authorization": "Bearer test-token"}
        )
        assert response.status_code == 202
        assert "workflow_id" in response.json()
```

---

## 11. Чеклист MVP

### Критичные эндпоинты (MVP)

- [ ] `POST /projects`
- [ ] `GET /projects`
- [ ] `GET /projects/{id}`
- [ ] `POST /projects/{id}/configs`
- [ ] `POST /projects/{id}/configs/validate`
- [ ] `POST /workflows`
- [ ] `GET /workflows`
- [ ] `GET /workflows/{id}`
- [ ] `DELETE /workflows/{id}`
- [ ] `POST /workflows/{id}/pause`
- [ ] `POST /workflows/{id}/resume`
- [ ] `GET /agents`
- [ ] `GET /agents/{id}`
- [ ] `GET /projects/{id}/budget`
- [ ] `POST /budget/alerts`
- [ ] `GET /events`
- [ ] `POST /webhooks`
- [ ] `GET /admin/audit-logs`
- [ ] `GET /admin/system/health`

### Можно отложить (Post-MVP)

- `PUT /projects/{id}`
- `DELETE /projects/{id}`
- `GET /projects/{id}/configs/{version}`
- `GET /projects/{id}/configs/{v1}/diff/{v2}`
- `POST /workflows/{id}/retry`
- `GET /workflows/{id}/steps`
- `GET /agents/{id}/logs`
- `GET /artifacts/{id}/download`
- `GET /webhooks/{id}/test`
- `PUT /admin/users/{id}/roles`

---

_Документ готов для передачи backend-команде_
