# AFL Orchestrator: Схема Базы Данных (Часть 2)

**Продолжение: остальные таблицы, индексы, миграции, оптимизация**

---

## 2. Физическая Схема Таблиц (продолжение)

### 2.6 Таблица: agents

```sql
-- Таблица регистрации агентов
CREATE TABLE agents (
    -- Primary Key
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Идентификация
    name VARCHAR(255) NOT NULL,
    type VARCHAR(50) NOT NULL,
    model VARCHAR(255),

    -- Статус
    status VARCHAR(50) NOT NULL DEFAULT 'idle',

    -- Текущая задача
    current_workflow_id UUID REFERENCES workflows(id) ON DELETE SET NULL,
    current_task_id UUID REFERENCES tasks(id) ON DELETE SET NULL,

    -- Конфигурация
    config JSONB DEFAULT '{}'::jsonb,
    capabilities TEXT[],  -- массив возможностей
    tools TEXT[],         -- доступные инструменты

    -- Метрики (денормализация)
    metrics JSONB DEFAULT '{}'::jsonb,

    -- Активность
    last_active_at TIMESTAMPTZ DEFAULT NOW(),
    last_error_at TIMESTAMPTZ,
    last_error_message TEXT,

    -- Временные метки
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Ограничения
    CONSTRAINT check_agent_status CHECK (status IN ('idle', 'busy', 'error', 'offline', 'maintenance')),
    CONSTRAINT check_agent_type CHECK (type IN ('llm', 'tool', 'hybrid', 'custom')),
    CONSTRAINT agents_name_unique UNIQUE (name)
);

-- Индексы
CREATE INDEX idx_agents_status ON agents(status);
CREATE INDEX idx_agents_type ON agents(type);
CREATE INDEX idx_agents_model ON agents(model);
CREATE INDEX idx_agents_last_active ON agents(last_active_at DESC);
CREATE INDEX idx_agents_current_workflow ON agents(current_workflow_id) WHERE current_workflow_id IS NOT NULL;
CREATE INDEX idx_agents_current_task ON agents(current_task_id) WHERE current_task_id IS NOT NULL;

-- GIN индексы
CREATE INDEX idx_agents_config ON agents USING GIN(config);
CREATE INDEX idx_agents_metrics ON agents USING GIN(metrics);
CREATE INDEX idx_agents_capabilities ON agents USING GIN(capabilities);

-- Частичный индекс для свободных агентов
CREATE INDEX idx_agents_idle ON agents(model, last_active_at)
    WHERE status = 'idle';

-- Комментарии
COMMENT ON TABLE agents IS 'Агенты системы - исполнители задач';
COMMENT ON COLUMN agents.config IS 'Конфигурация агента: {temperature, max_tokens, timeout}';
COMMENT ON COLUMN agents.capabilities IS 'Список возможностей: ["code_analysis", "review", "documentation"]';
COMMENT ON COLUMN agents.tools IS 'Доступные инструменты: ["git_clone", "file_read", "http_request"]';
COMMENT ON COLUMN agents.metrics IS 'Метрики: {tasks_completed, tokens_used_total, success_rate}';

-- Триггер updated_at
CREATE TRIGGER update_agents_updated_at
    BEFORE UPDATE ON agents
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Триггер для обновления last_active_at
CREATE OR REPLACE FUNCTION update_agent_last_active()
RETURNS TRIGGER AS $$
BEGIN
    NEW.last_active_at := NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER agent_activity_update
    BEFORE UPDATE ON agents
    FOR EACH ROW
    WHEN (OLD.status IS DISTINCT FROM NEW.status OR OLD.current_task_id IS DISTINCT FROM NEW.current_task_id)
    EXECUTE FUNCTION update_agent_last_active();
```

### 2.7 Таблица: artifacts

```sql
-- Таблица артефактов
CREATE TABLE artifacts (
    -- Primary Key
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Связи
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    workflow_id UUID REFERENCES workflows(id) ON DELETE SET NULL,
    task_id UUID REFERENCES tasks(id) ON DELETE SET NULL,

    -- Информация
    name VARCHAR(255) NOT NULL,
    type VARCHAR(50) NOT NULL,
    description TEXT,

    -- Хранение
    storage_path VARCHAR(500) NOT NULL,
    storage_provider VARCHAR(50) NOT NULL DEFAULT 's3',
    size_bytes BIGINT NOT NULL DEFAULT 0,
    mime_type VARCHAR(255),
    checksum VARCHAR(100),  -- SHA256

    -- Версионирование
    version INTEGER NOT NULL DEFAULT 1,
    parent_artifact_id UUID REFERENCES artifacts(id) ON DELETE SET NULL,

    -- Доступы
    visibility VARCHAR(50) NOT NULL DEFAULT 'private',
    permissions JSONB DEFAULT '{}'::jsonb,

    -- Метаданные
    metadata JSONB DEFAULT '{}'::jsonb,

    -- Автор
    created_by UUID REFERENCES users(id) ON DELETE SET NULL,

    -- Временные метки
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ,  -- для временных артефактов

    -- Ограничения
    CONSTRAINT check_artifact_type CHECK (type IN ('file', 'directory', 'json', 'text', 'image', 'archive', 'database')),
    CONSTRAINT check_artifact_visibility CHECK (visibility IN ('private', 'project', 'public')),
    CONSTRAINT check_artifact_size CHECK (size_bytes >= 0),
    CONSTRAINT artifacts_storage_path_unique UNIQUE (storage_provider, storage_path)
);

-- Индексы
CREATE INDEX idx_artifacts_project_id ON artifacts(project_id);
CREATE INDEX idx_artifacts_workflow_id ON artifacts(workflow_id);
CREATE INDEX idx_artifacts_task_id ON artifacts(task_id);
CREATE INDEX idx_artifacts_type ON artifacts(type);
CREATE INDEX idx_artifacts_created_at ON artifacts(created_at DESC);
CREATE INDEX idx_artifacts_created_by ON artifacts(created_by);

-- Составной индекс для поиска артефактов проекта
CREATE INDEX idx_artifacts_project_type ON artifacts(project_id, type, created_at DESC);

-- Частичный индекс для активных артефактов
CREATE INDEX idx_artifacts_active ON artifacts(project_id, created_at DESC)
    WHERE expires_at IS NULL OR expires_at > NOW();

-- GIN индексы
CREATE INDEX idx_artifacts_metadata ON artifacts USING GIN(metadata);
CREATE INDEX idx_artifacts_permissions ON artifacts USING GIN(permissions);

-- Комментарии
COMMENT ON TABLE artifacts IS 'Артефакты workflow - файлы и результаты';
COMMENT ON COLUMN artifacts.storage_path IS 'Путь к файлу в хранилище (S3, MinIO, etc.)';
COMMENT ON COLUMN artifacts.checksum IS 'SHA256 хеш файла для проверки целостности';
COMMENT ON COLUMN artifacts.visibility IS 'Уровень доступа: private, project, public';
COMMENT ON COLUMN artifacts.metadata IS 'Метаданные: {files_count, commit_hash, analysis_results}';

-- Триггер updated_at (если понадобится)
-- Для artifacts обычно не нужен, так как они immutable
```

### 2.8 Таблица: events

```sql
-- Таблица событий системы
-- Партиционирована по времени (месяц)
CREATE TABLE events (
    -- Primary Key
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Тип события
    event_type VARCHAR(100) NOT NULL,
    category VARCHAR(50) NOT NULL,  -- workflow, agent, budget, security

    -- Источник
    source_type VARCHAR(50) NOT NULL,
    source_id UUID NOT NULL,
    project_id UUID,

    -- Данные события
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,

    -- Обработка
    processed BOOLEAN NOT NULL DEFAULT FALSE,
    processed_at TIMESTAMPTZ,
    processed_by VARCHAR(100),

    -- Доставка webhook
    webhook_deliveries INTEGER NOT NULL DEFAULT 0,

    -- Временные метки
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Ограничения
    CONSTRAINT check_event_category CHECK (category IN ('workflow', 'agent', 'budget', 'security', 'config', 'system'))
) PARTITION BY RANGE (created_at);

-- Партиции по месяцам (пример на 2026 год)
CREATE TABLE events_2026_01 PARTITION OF events
    FOR VALUES FROM ('2026-01-01') TO ('2026-02-01');

CREATE TABLE events_2026_02 PARTITION OF events
    FOR VALUES FROM ('2026-02-01') TO ('2026-03-01');

CREATE TABLE events_2026_03 PARTITION OF events
    FOR VALUES FROM ('2026-03-01') TO ('2026-04-01');

-- Индексы (создаются автоматически на партициях)
CREATE INDEX idx_events_type ON events(event_type);
CREATE INDEX idx_events_category ON events(category);
CREATE INDEX idx_events_source ON events(source_type, source_id);
CREATE INDEX idx_events_project ON events(project_id);
CREATE INDEX idx_events_created_at ON events(created_at DESC);
CREATE INDEX idx_events_unprocessed ON events(created_at) WHERE processed = FALSE;

-- GIN индекс для payload
CREATE INDEX idx_events_payload ON events USING GIN(payload);

-- BRIN индекс для временных запросов
CREATE INDEX idx_events_created_at_brin ON events USING BRIN(created_at);

-- Комментарии
COMMENT ON TABLE events IS 'События системы для webhook и аудита';
COMMENT ON COLUMN events.payload IS 'Данные события в JSON формате';
COMMENT ON COLUMN events.processed IS 'Флаг обработки события (для webhook)';

-- TTL для автоматического удаления старых событий
-- Настройка через pg_cron или внешний job
```

### 2.9 Таблица: audit_logs

```sql
-- Таблица аудита действий
-- Immutable - только INSERT
CREATE TABLE audit_logs (
    -- Primary Key
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Пользователь
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    user_email VARCHAR(255),  -- денормализация для истории
    user_name VARCHAR(255),   -- денормализация для истории

    -- Действие
    action VARCHAR(100) NOT NULL,  -- формат: "resource.operation"
    resource_type VARCHAR(50) NOT NULL,
    resource_id UUID,

    -- Контекст
    ip_address INET,
    user_agent TEXT,
    request_id UUID,

    -- Результат
    status VARCHAR(50) NOT NULL,  -- success, failure, forbidden
    error_code VARCHAR(100),
    error_message TEXT,

    -- Детали
    details JSONB DEFAULT '{}'::jsonb,
    changes JSONB,  -- для UPDATE: {old, new}

    -- Временные метки
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Ограничения
    CONSTRAINT check_audit_status CHECK (status IN ('success', 'failure', 'forbidden', 'error')),
    CONSTRAINT check_action_format CHECK (action ~ '^[a-z_]+\.[a-z_]+$')
) PARTITION BY RANGE (created_at);

-- Партиции по месяцам
CREATE TABLE audit_logs_2026_01 PARTITION OF audit_logs
    FOR VALUES FROM ('2026-01-01') TO ('2026-02-01');

CREATE TABLE audit_logs_2026_02 PARTITION OF audit_logs
    FOR VALUES FROM ('2026-02-01') TO ('2026-03-01');

CREATE TABLE audit_logs_2026_03 PARTITION OF audit_logs
    FOR VALUES FROM ('2026-03-01') TO ('2026-04-01');

-- Индексы
CREATE INDEX idx_audit_logs_user_id ON audit_logs(user_id);
CREATE INDEX idx_audit_logs_action ON audit_logs(action);
CREATE INDEX idx_audit_logs_resource ON audit_logs(resource_type, resource_id);
CREATE INDEX idx_audit_logs_status ON audit_logs(status);
CREATE INDEX idx_audit_logs_created_at ON audit_logs(created_at DESC);
CREATE INDEX idx_audit_logs_ip ON audit_logs(ip_address);

-- Составной индекс для поиска действий пользователя
CREATE INDEX idx_audit_logs_user_action ON audit_logs(user_id, action, created_at DESC);

-- Частичный индекс для неудачных операций
CREATE INDEX idx_audit_logs_failures ON audit_logs(created_at DESC)
    WHERE status IN ('failure', 'forbidden', 'error');

-- GIN индексы
CREATE INDEX idx_audit_logs_details ON audit_logs USING GIN(details);
CREATE INDEX idx_audit_logs_changes ON audit_logs USING GIN(changes);

-- BRIN индекс
CREATE INDEX idx_audit_logs_created_at_brin ON audit_logs USING BRIN(created_at);

-- Комментарии
COMMENT ON TABLE audit_logs IS 'Аудит всех действий пользователей (immutable)';
COMMENT ON COLUMN audit_logs.changes IS 'Старые и новые значения для UPDATE операций';
COMMENT ON COLUMN audit_logs.details IS 'Дополнительные детали операции';

-- Запрет UPDATE и DELETE для audit_logs
REVOKE UPDATE, DELETE ON audit_logs FROM orchestrator_readwrite;
GRANT INSERT ON audit_logs TO orchestrator_readwrite;
```

### 2.10 Таблица: budget_transactions

```sql
-- Таблица транзакций бюджета
-- Партиционирована по времени
CREATE TABLE budget_transactions (
    -- Primary Key
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Связи
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    workflow_id UUID REFERENCES workflows(id) ON DELETE SET NULL,
    task_id UUID REFERENCES tasks(id) ON DELETE SET NULL,

    -- Провайдер и модель
    provider VARCHAR(50) NOT NULL,  -- openai, anthropic, azure
    model VARCHAR(255) NOT NULL,

    -- Токены
    prompt_tokens INTEGER NOT NULL DEFAULT 0,
    completion_tokens INTEGER NOT NULL DEFAULT 0,
    total_tokens INTEGER NOT NULL DEFAULT 0,

    -- Стоимость
    cost_usd NUMERIC(12, 6) NOT NULL DEFAULT 0,
    cost_per_1k_tokens NUMERIC(10, 6),  -- цена за 1000 токенов

    -- Детали
    transaction_type VARCHAR(50) NOT NULL DEFAULT 'llm_call',
    metadata JSONB DEFAULT '{}'::jsonb,

    -- Временные метки
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Ограничения
    CONSTRAINT check_transaction_type CHECK (transaction_type IN ('llm_call', 'embedding', 'fine_tuning', 'adjustment', 'refund')),
    CONSTRAINT check_tokens_positive CHECK (prompt_tokens >= 0 AND completion_tokens >= 0 AND total_tokens >= 0),
    CONSTRAINT check_total_tokens CHECK (total_tokens = prompt_tokens + completion_tokens),
    CONSTRAINT check_cost_positive CHECK (cost_usd >= 0)
) PARTITION BY RANGE (created_at);

-- Партиции по месяцам
CREATE TABLE budget_transactions_2026_01 PARTITION OF budget_transactions
    FOR VALUES FROM ('2026-01-01') TO ('2026-02-01');

CREATE TABLE budget_transactions_2026_02 PARTITION OF budget_transactions
    FOR VALUES FROM ('2026-02-01') TO ('2026-03-01');

CREATE TABLE budget_transactions_2026_03 PARTITION OF budget_transactions
    FOR VALUES FROM ('2026-03-01') TO ('2026-04-01');

-- Индексы
CREATE INDEX idx_budget_transactions_project ON budget_transactions(project_id);
CREATE INDEX idx_budget_transactions_workflow ON budget_transactions(workflow_id);
CREATE INDEX idx_budget_transactions_task ON budget_transactions(task_id);
CREATE INDEX idx_budget_transactions_provider ON budget_transactions(provider);
CREATE INDEX idx_budget_transactions_model ON budget_transactions(model);
CREATE INDEX idx_budget_transactions_created_at ON budget_transactions(created_at DESC);

-- Составной индекс для агрегации по проекту и провайдеру
CREATE INDEX idx_budget_project_provider_date ON budget_transactions(project_id, provider, created_at DESC);

-- BRIN индекс для временных запросов
CREATE INDEX idx_budget_transactions_created_at_brin ON budget_transactions USING BRIN(created_at);

-- GIN индекс для metadata
CREATE INDEX idx_budget_transactions_metadata ON budget_transactions USING GIN(metadata);

-- Комментарии
COMMENT ON TABLE budget_transactions IS 'Транзакции учёта токенов и затрат';
COMMENT ON COLUMN budget_transactions.cost_per_1k_tokens IS 'Цена за 1000 токенов на момент транзакции';
COMMENT ON COLUMN budget_transactions.metadata IS 'Детали транзакции: {request_id, duration_ms, cached}';

-- Представление для агрегации затрат по проекту
CREATE VIEW project_budget_summary AS
SELECT
    project_id,
    DATE_TRUNC('month', created_at) AS month,
    provider,
    model,
    SUM(total_tokens) AS total_tokens,
    SUM(cost_usd) AS total_cost_usd,
    COUNT(*) AS transaction_count
FROM budget_transactions
GROUP BY project_id, DATE_TRUNC('month', created_at), provider, model;
```

### 2.11 Таблица: api_keys

```sql
-- Таблица API ключей
CREATE TABLE api_keys (
    -- Primary Key
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Владелец
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,

    -- Информация
    name VARCHAR(255) NOT NULL,
    description TEXT,

    -- Ключ (хеш)
    key_hash VARCHAR(255) NOT NULL,
    key_prefix VARCHAR(20) NOT NULL,  -- первые символы для идентификации (например: afl_sk_abc123)

    -- Права доступа
    scopes TEXT[] NOT NULL DEFAULT '{}',

    -- Срок действия
    expires_at TIMESTAMPTZ,

    -- Использование
    last_used_at TIMESTAMPTZ,
    last_used_ip INET,
    usage_count INTEGER NOT NULL DEFAULT 0,

    -- Статус
    status VARCHAR(50) NOT NULL DEFAULT 'active',
    revoked_at TIMESTAMPTZ,
    revoked_reason TEXT,

    -- Временные метки
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Ограничения
    CONSTRAINT check_api_key_status CHECK (status IN ('active', 'revoked', 'expired')),
    CONSTRAINT api_keys_key_hash_unique UNIQUE (key_hash)
);

-- Индексы
CREATE INDEX idx_api_keys_user_id ON api_keys(user_id);
CREATE INDEX idx_api_keys_key_hash ON api_keys(key_hash);
CREATE INDEX idx_api_keys_key_prefix ON api_keys(key_prefix);
CREATE INDEX idx_api_keys_status ON api_keys(status);
CREATE INDEX idx_api_keys_expires_at ON api_keys(expires_at) WHERE expires_at IS NOT NULL;

-- Частичный индекс для активных ключей
CREATE INDEX idx_api_keys_active ON api_keys(user_id, created_at DESC)
    WHERE status = 'active' AND (expires_at IS NULL OR expires_at > NOW());

-- Комментарии
COMMENT ON TABLE api_keys IS 'API ключи пользователей для аутентификации';
COMMENT ON COLUMN api_keys.key_hash IS 'SHA256 хеш полного ключа';
COMMENT ON COLUMN api_keys.key_prefix IS 'Префикс ключа для отображения в UI';
COMMENT ON COLUMN api_keys.scopes IS 'Разрешения: ["projects:read", "workflows:create"]';

-- Триггер updated_at
CREATE TRIGGER update_api_keys_updated_at
    BEFORE UPDATE ON api_keys
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
```

### 2.12 Таблица: user_projects

```sql
-- Таблица связи пользователей с проектами (многие-ко-многим)
CREATE TABLE user_projects (
    -- Composite Primary Key
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,

    -- Роль в проекте
    role VARCHAR(50) NOT NULL DEFAULT 'member',

    -- Кто добавил
    granted_by UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    granted_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Ограничения
    CONSTRAINT check_project_role CHECK (role IN ('owner', 'admin', 'member', 'viewer')),
    CONSTRAINT user_projects_pkey PRIMARY KEY (user_id, project_id)
);

-- Индексы
CREATE INDEX idx_user_projects_user_id ON user_projects(user_id);
CREATE INDEX idx_user_projects_project_id ON user_projects(project_id);
CREATE INDEX idx_user_projects_role ON user_projects(project_id, role);

-- Частичный индекс для владельцев проектов
CREATE INDEX idx_user_projects_owners ON user_projects(project_id) WHERE role = 'owner';

-- Комментарии
COMMENT ON TABLE user_projects IS 'Связь пользователей с проектами (многие-ко-многим)';
COMMENT ON COLUMN user_projects.role IS 'Роль в проекте: owner, admin, member, viewer';

-- Триггер для предотвращения удаления последнего владельца
CREATE OR REPLACE FUNCTION prevent_last_owner_removal()
RETURNS TRIGGER AS $$
BEGIN
    IF OLD.role = 'owner' THEN
        -- Проверяем, есть ли другие владельцы
        IF NOT EXISTS (
            SELECT 1 FROM user_projects
            WHERE project_id = OLD.project_id AND role = 'owner' AND user_id != OLD.user_id
        ) THEN
            RAISE EXCEPTION 'Cannot remove the last owner of a project';
        END IF;
    END IF;
    RETURN OLD;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER check_last_owner_before_delete
    BEFORE DELETE ON user_projects
    FOR EACH ROW
    EXECUTE FUNCTION prevent_last_owner_removal();
```

### 2.13 Таблица: webhooks

```sql
-- Таблица настроек webhook
CREATE TABLE webhooks (
    -- Primary Key
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Связь с проектом
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,

    -- Конфигурация
    url VARCHAR(500) NOT NULL,
    events TEXT[] NOT NULL DEFAULT '{}',
    secret VARCHAR(255) NOT NULL,  -- для HMAC подписи

    -- Статус
    active BOOLEAN NOT NULL DEFAULT TRUE,

    -- Retry политика
    retry_policy JSONB DEFAULT '{"max_retries": 3, "backoff_seconds": 60}'::jsonb,

    -- Дополнительные headers
    headers JSONB DEFAULT '{}'::jsonb,

    -- Статистика
    stats JSONB DEFAULT '{"total_deliveries": 0, "successful": 0, "failed": 0}'::jsonb,

    -- Временные метки
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_delivery_at TIMESTAMPTZ,

    -- Ограничения
    CONSTRAINT check_webhook_url CHECK (url ~ '^https?://')
);

-- Индексы
CREATE INDEX idx_webhooks_project_id ON webhooks(project_id);
CREATE INDEX idx_webhooks_active ON webhooks(project_id) WHERE active = TRUE;

-- GIN индекс для events
CREATE INDEX idx_webhooks_events ON webhooks USING GIN(events);

-- Комментарии
COMMENT ON TABLE webhooks IS 'Настройки webhook для уведомлений';
COMMENT ON COLUMN webhooks.secret IS 'Секрет для HMAC-SHA256 подписи payload';
COMMENT ON COLUMN webhooks.retry_policy IS 'Политика повторных попыток: {max_retries, backoff_seconds}';

-- Триггер updated_at
CREATE TRIGGER update_webhooks_updated_at
    BEFORE UPDATE ON webhooks
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
```

### 2.14 Таблица: webhook_deliveries

```sql
-- Таблица истории доставок webhook
CREATE TABLE webhook_deliveries (
    -- Primary Key
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Связи
    webhook_id UUID NOT NULL REFERENCES webhooks(id) ON DELETE CASCADE,
    event_id UUID REFERENCES events(id) ON DELETE SET NULL,

    -- Статус доставки
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    http_status INTEGER,

    -- Запрос
    request_headers JSONB,
    request_body TEXT,

    -- Ответ
    response_headers JSONB,
    response_body TEXT,

    -- Попытки
    attempt_count INTEGER NOT NULL DEFAULT 1,
    max_attempts INTEGER NOT NULL DEFAULT 3,

    -- Временные метки
    scheduled_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    delivered_at TIMESTAMPTZ,
    next_retry_at TIMESTAMPTZ,

    -- Ошибка
    error_message TEXT,

    -- Ограничения
    CONSTRAINT check_delivery_status CHECK (status IN ('pending', 'sent', 'failed', 'cancelled')),
    CONSTRAINT check_attempt_count CHECK (attempt_count >= 1 AND attempt_count <= max_attempts)
) PARTITION BY RANGE (scheduled_at);

-- Партиции по месяцам
CREATE TABLE webhook_deliveries_2026_01 PARTITION OF webhook_deliveries
    FOR VALUES FROM ('2026-01-01') TO ('2026-02-01');

CREATE TABLE webhook_deliveries_2026_02 PARTITION OF webhook_deliveries
    FOR VALUES FROM ('2026-02-01') TO ('2026-03-01');

-- Индексы
CREATE INDEX idx_webhook_deliveries_webhook ON webhook_deliveries(webhook_id);
CREATE INDEX idx_webhook_deliveries_event ON webhook_deliveries(event_id);
CREATE INDEX idx_webhook_deliveries_status ON webhook_deliveries(status);
CREATE INDEX idx_webhook_deliveries_scheduled ON webhook_deliveries(scheduled_at DESC);

-- Частичный индекс для ожидающих доставок
CREATE INDEX idx_webhook_deliveries_pending ON webhook_deliveries(scheduled_at ASC)
    WHERE status = 'pending' AND next_retry_at IS NULL;

-- BRIN индекс
CREATE INDEX idx_webhook_deliveries_scheduled_brin ON webhook_deliveries USING BRIN(scheduled_at);

-- Комментарии
COMMENT ON TABLE webhook_deliveries IS 'История доставок webhook уведомлений';
```

### 2.15 Таблица: budget_alerts

```sql
-- Таблица алертов бюджета
CREATE TABLE budget_alerts (
    -- Primary Key
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Связь с проектом
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,

    -- Тип алерта
    alert_type VARCHAR(50) NOT NULL,
    threshold NUMERIC(10, 4) NOT NULL,

    -- Каналы уведомлений
    notification_channels TEXT[] NOT NULL DEFAULT '{}',
    webhook_url VARCHAR(500),

    -- Статус
    enabled BOOLEAN NOT NULL DEFAULT TRUE,

    -- Шаблон сообщения
    message_template TEXT,

    -- Последнее срабатывание
    last_triggered_at TIMESTAMPTZ,
    last_triggered_value NUMERIC(10, 4),

    -- Временные метки
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by UUID REFERENCES users(id) ON DELETE SET NULL,

    -- Ограничения
    CONSTRAINT check_alert_type CHECK (alert_type IN ('percentage', 'absolute', 'forecast')),
    CONSTRAINT check_threshold_percentage CHECK (
        (alert_type = 'percentage' AND threshold >= 0 AND threshold <= 100) OR
        (alert_type != 'percentage')
    )
);

-- Индексы
CREATE INDEX idx_budget_alerts_project ON budget_alerts(project_id);
CREATE INDEX idx_budget_alerts_type ON budget_alerts(alert_type);
CREATE INDEX idx_budget_alerts_enabled ON budget_alerts(project_id, enabled) WHERE enabled = TRUE;

-- Комментарии
COMMENT ON TABLE budget_alerts IS 'Алерты для уведомлений о бюджете';
COMMENT ON COLUMN budget_alerts.threshold IS 'Порог срабатывания (проценты или абсолютное значение)';

-- Триггер updated_at
CREATE TRIGGER update_budget_alerts_updated_at
    BEFORE UPDATE ON budget_alerts
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
```

### 2.16 Таблица: task_attempts

```sql
-- Таблица попыток выполнения задач
CREATE TABLE task_attempts (
    -- Primary Key
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Связь с задачей
    task_id UUID NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,

    -- Номер попытки
    attempt_number INTEGER NOT NULL,

    -- Статус
    status VARCHAR(50) NOT NULL DEFAULT 'running',

    -- Ошибка
    error JSONB,

    -- Временные метки
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ,

    -- Метрики
    tokens_used INTEGER NOT NULL DEFAULT 0,
    duration_ms INTEGER,

    -- Ограничения
    CONSTRAINT check_attempt_number CHECK (attempt_number >= 1),
    CONSTRAINT check_attempt_status CHECK (status IN ('running', 'completed', 'failed')),
    CONSTRAINT task_attempts_unique UNIQUE (task_id, attempt_number)
);

-- Индексы
CREATE INDEX idx_task_attempts_task_id ON task_attempts(task_id);
CREATE INDEX idx_task_attempts_status ON task_attempts(status);
CREATE INDEX idx_task_attempts_started ON task_attempts(started_at DESC);

-- Частичный индекс для активных попыток
CREATE INDEX idx_task_attempts_running ON task_attempts(task_id)
    WHERE status = 'running';

-- Комментарии
COMMENT ON TABLE task_attempts IS 'История попыток выполнения задач (для retry)';
```

---

## 3. Индексы и Оптимизация

### 3.1 Стратегия Индексации

| Таблица                 | Индексы                        | Тип                      | Обоснование                              |
| ----------------------- | ------------------------------ | ------------------------ | ---------------------------------------- |
| **users**               | email (unique), role, status   | B-tree                   | Частые фильтры по статусу и роли         |
| **workflows**           | project_id, status, created_at | B-tree composite         | Основной запрос: список workflow проекта |
| **workflows**           | status WHERE active            | Partial                  | Быстрый поиск активных workflow          |
| **workflows**           | metadata                       | GIN                      | Поиск по произвольным полям              |
| **workflows**           | created_at                     | BRIN                     | Эффективно для временных диапазонов      |
| **tasks**               | workflow_id, step_order        | B-tree                   | Получение задач workflow по порядку      |
| **tasks**               | status WHERE pending           | Partial                  | Выборка ожидающих задач                  |
| **events**              | created_at                     | BRIN + партиционирование | Очень большая таблица                    |
| **audit_logs**          | user_id, created_at            | B-tree composite         | Аудит действий пользователя              |
| **budget_transactions** | project_id, created_at         | BRIN + партиционирование | Агрегация по проекту                     |

### 3.2 Специальные Индексы

#### GIN для JSONB полей

```sql
-- Для поиска по любому ключу в JSONB
CREATE INDEX idx_workflows_metadata_gin ON workflows USING GIN(metadata);

-- Для поиска по конкретному ключу (быстрее)
CREATE INDEX idx_workflows_metadata_triggered_by ON workflows ((metadata->>'triggered_by'));

-- Для массивов в JSONB
CREATE INDEX idx_webhooks_events_gin ON webhooks USING GIN(events);
```

#### Частичные Индексы

```sql
-- Только активные workflow
CREATE INDEX idx_workflows_running ON workflows(project_id, created_at DESC)
    WHERE status = 'running';

-- Только неудачные попытки
CREATE INDEX idx_tasks_failed_retryable ON tasks(workflow_id, retry_count)
    WHERE status = 'failed' AND retry_count < max_retries;

-- Только активные API ключи
CREATE INDEX idx_api_keys_not_expired ON api_keys(user_id)
    WHERE status = 'active' AND (expires_at IS NULL OR expires_at > NOW());
```

#### Покрывающие Индексы (Covering)

```sql
-- Для запроса: SELECT id, status FROM workflows WHERE project_id = $1
CREATE INDEX idx_workflows_project_status_covering
    ON workflows(project_id, status) INCLUDE (id);
```

### 3.3 Анализ Типичных Запросов

#### Запрос 1: Список активных workflow проекта

```sql
-- Запрос
SELECT id, status, current_step, progress, created_at
FROM workflows
WHERE project_id = 'proj-123'
  AND status IN ('running', 'paused')
ORDER BY created_at DESC
LIMIT 20;

-- EXPLAIN ANALYZE
-- Ожидаемый план:
-- Limit  (cost=0.43..10.45 rows=20)
--   ->  Index Scan Backward using idx_workflows_active on workflows
--         Index Cond: (project_id = 'proj-123'::uuid)
--         Filter: (status = ANY ('{running,paused}'::text[]))

-- Рекомендация: Использовать частичный индекс idx_workflows_active
```

#### Запрос 2: Агрегация затрат по проекту

```sql
-- Запрос
SELECT
    provider,
    model,
    SUM(total_tokens) as tokens,
    SUM(cost_usd) as cost
FROM budget_transactions
WHERE project_id = 'proj-123'
  AND created_at >= NOW() - INTERVAL '30 days'
GROUP BY provider, model
ORDER BY cost DESC;

-- Рекомендация:
-- 1. Использовать партиционирование по created_at
-- 2. Индекс idx_budget_project_provider_date
-- 3. BRIN индекс для временных диапазонов
```

#### Запрос 3: Получение задач для выполнения

```sql
-- Запрос
SELECT t.*, a.model as agent_model
FROM tasks t
JOIN agents a ON t.agent_id = a.id
WHERE t.status = 'pending'
  AND t.workflow_id IN (
      SELECT id FROM workflows WHERE status = 'running'
  )
ORDER BY t.step_order ASC
LIMIT 10;

-- Рекомендация:
-- 1. Частичный индекс idx_tasks_pending
-- 2. Индекс на workflows(status)
```

#### Запрос 4: Аудит действий пользователя

```sql
-- Запрос
SELECT action, resource_type, resource_id, status, created_at
FROM audit_logs
WHERE user_id = 'user-123'
  AND created_at >= NOW() - INTERVAL '7 days'
ORDER BY created_at DESC
LIMIT 50;

-- Рекомендация:
-- 1. Составной индекс idx_audit_logs_user_action (user_id, created_at DESC)
-- 2. Партиционирование по времени
```

#### Запрос 5: Обновление прогресса workflow

```sql
-- Запрос
UPDATE workflows
SET completed_steps = completed_steps + 1,
    status = CASE
        WHEN completed_steps + 1 >= total_steps THEN 'completed'
        ELSE status
    END,
    completed_at = CASE
        WHEN completed_steps + 1 >= total_steps THEN NOW()
        ELSE completed_at
    END
WHERE id = 'wf-123';

-- Рекомендация:
-- 1. Триггер для автоматического обновления progress
-- 2. Триггер для updated_at
```

---

**Продолжение в части 3: миграции Alembic, безопасность, backup**
