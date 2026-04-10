# AFL Orchestrator: Схема Базы Данных (Часть 3)

**Миграции Alembic, Безопасность, Backup, Мониторинг**

---

## 4. Миграции (Alembic)

### 4.1 Структура Миграций

```
/migrations
├── versions/
│   ├── 001_initial_schema.py
│   ├── 002_add_users_and_auth.py
│   ├── 003_add_agents_table.py
│   ├── 004_add_budget_tracking.py
│   ├── 005_add_audit_logs.py
│   ├── 006_add_webhooks.py
│   ├── 007_add_indexes_performance.py
│   └── 008_add_partitioning.py
├── env.py
├── script.py.mako
└── README.md
```

### 4.2 Примеры Миграций

#### Миграция 001: Initial Schema

```python
"""Initial schema - projects, configs, workflows, tasks

Revision ID: 001
Revises:
Create Date: 2026-03-31 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Enable UUID extension
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')

    # Create updated_at trigger function
    op.execute("""
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)

    # === projects ===
    op.create_table('projects',
        sa.Column('id', postgresql.UUID(as_uuid=True),
                  server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('owner_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('status', sa.String(50), nullable=False,
                  server_default='active'),
        sa.Column('settings', postgresql.JSONB(astext_type=sa.Text()),
                  server_default='{}', nullable=False),
        sa.Column('budget_config', postgresql.JSONB(astext_type=sa.Text()),
                  server_default='{}', nullable=False),
        sa.Column('stats', postgresql.JSONB(astext_type=sa.Text()),
                  server_default='{}', nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True),
                  nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True),
                  nullable=False, server_default=sa.text('NOW()')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('owner_id', 'name', name='uq_projects_owner_name'),
        sa.CheckConstraint(
            "status IN ('active', 'archived', 'deleted')",
            name='check_project_status'
        )
    )

    # === config_versions ===
    op.create_table('config_versions',
        sa.Column('id', postgresql.UUID(as_uuid=True),
                  server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('version', sa.String(50), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('format', sa.String(20), nullable=False, server_default='yaml'),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('validation_status', sa.String(50), nullable=False,
                  server_default='pending'),
        sa.Column('validation_result', postgresql.JSONB(astext_type=sa.Text()),
                  server_default='{}', nullable=False),
        sa.Column('changelog', sa.Text(), nullable=True),
        sa.Column('is_latest', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('parent_version_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True),
                  nullable=False, server_default=sa.text('NOW()')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('project_id', 'version', name='uq_config_project_version'),
        sa.CheckConstraint(
            "format IN ('yaml', 'json')",
            name='check_config_format'
        ),
        sa.CheckConstraint(
            "validation_status IN ('pending', 'valid', 'invalid', 'warnings')",
            name='check_validation_status'
        ),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['parent_version_id'], ['config_versions.id'], ondelete='SET NULL'),
    )

    # === workflows ===
    op.create_table('workflows',
        sa.Column('id', postgresql.UUID(as_uuid=True),
                  server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('config_version_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('status', sa.String(50), nullable=False, server_default='pending'),
        sa.Column('priority', sa.String(20), nullable=False, server_default='normal'),
        sa.Column('current_step', sa.String(255), nullable=True),
        sa.Column('total_steps', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('completed_steps', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('failed_steps', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('progress', sa.Numeric(5, 4), nullable=False, server_default='0'),
        sa.Column('started_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('paused_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('resumed_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('completed_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('failed_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('cancelled_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('current_state', postgresql.JSONB(astext_type=sa.Text()),
                  server_default='{}', nullable=False),
        sa.Column('parameters', postgresql.JSONB(astext_type=sa.Text()),
                  server_default='{}', nullable=False),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()),
                  server_default='{}', nullable=False),
        sa.Column('tokens_used', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('cost_usd', sa.Numeric(12, 6), nullable=False, server_default='0'),
        sa.Column('estimated_duration', sa.Integer(), nullable=True),
        sa.Column('error_code', sa.String(100), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('webhook_url', sa.String(500), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True),
                  nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True),
                  nullable=False, server_default=sa.text('NOW()')),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint(
            "status IN ('pending', 'queued', 'running', 'paused', 'completed', 'failed', 'cancelled')",
            name='check_workflow_status'
        ),
        sa.CheckConstraint(
            "priority IN ('low', 'normal', 'high', 'critical')",
            name='check_workflow_priority'
        ),
        sa.CheckConstraint(
            'progress >= 0 AND progress <= 1',
            name='check_progress_range'
        ),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['config_version_id'], ['config_versions.id'], ondelete='RESTRICT'),
    )

    # === tasks ===
    op.create_table('tasks',
        sa.Column('id', postgresql.UUID(as_uuid=True),
                  server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('workflow_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('agent_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('parent_task_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('step_order', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(50), nullable=False, server_default='pending'),
        sa.Column('input_context', postgresql.JSONB(astext_type=sa.Text()),
                  server_default='{}', nullable=False),
        sa.Column('output', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('error', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('retry_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('max_retries', sa.Integer(), nullable=False, server_default='3'),
        sa.Column('scheduled_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('started_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('completed_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('tokens_used', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('duration_ms', sa.Integer(), nullable=True),
        sa.Column('config', postgresql.JSONB(astext_type=sa.Text()),
                  server_default='{}', nullable=False),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()),
                  server_default='{}', nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True),
                  nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True),
                  nullable=False, server_default=sa.text('NOW()')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('workflow_id', 'step_order', name='uq_tasks_workflow_step'),
        sa.CheckConstraint(
            "status IN ('pending', 'queued', 'running', 'completed', 'failed', 'skipped', 'cancelled')",
            name='check_task_status'
        ),
        sa.CheckConstraint(
            'retry_count >= 0 AND retry_count <= max_retries',
            name='check_retry_count'
        ),
        sa.ForeignKeyConstraint(['workflow_id'], ['workflows.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['agent_id'], ['agents.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['parent_task_id'], ['tasks.id'], ondelete='SET NULL'),
    )

    # === Indexes for projects ===
    op.create_index('idx_projects_owner_id', 'projects', ['owner_id'])
    op.create_index('idx_projects_status', 'projects', ['status'])
    op.create_index('idx_projects_created_at', 'projects', ['created_at'], postgresql_using='btree', unique=False)
    op.create_index('idx_projects_active', 'projects', ['owner_id', 'created_at'],
                    postgresql_where=sa.text("status = 'active'"))

    # === Indexes for workflows ===
    op.create_index('idx_workflows_project_id', 'workflows', ['project_id'])
    op.create_index('idx_workflows_status', 'workflows', ['status'])
    op.create_index('idx_workflows_created_at', 'workflows', ['created_at'], postgresql_using='btree')
    op.create_index('idx_workflows_config_version', 'workflows', ['config_version_id'])
    op.create_index('idx_workflows_active', 'workflows', ['project_id', 'created_at'],
                    postgresql_where=sa.text("status IN ('running', 'paused')"))
    op.create_index('idx_workflows_queued', 'workflows', ['priority', 'created_at'],
                    postgresql_where=sa.text("status = 'queued'"))

    # === Indexes for tasks ===
    op.create_index('idx_tasks_workflow_id', 'tasks', ['workflow_id'])
    op.create_index('idx_tasks_step_order', 'tasks', ['workflow_id', 'step_order'])
    op.create_index('idx_tasks_status', 'tasks', ['status'])
    op.create_index('idx_tasks_pending', 'tasks', ['workflow_id', 'step_order'],
                    postgresql_where=sa.text("status = 'pending'"))

    # === Triggers for updated_at ===
    op.execute("""
        CREATE TRIGGER update_projects_updated_at
        BEFORE UPDATE ON projects
        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    """)

    op.execute("""
        CREATE TRIGGER update_workflows_updated_at
        BEFORE UPDATE ON workflows
        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    """)

    op.execute("""
        CREATE TRIGGER update_tasks_updated_at
        BEFORE UPDATE ON tasks
        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    """)


def downgrade():
    # Drop triggers
    op.execute('DROP TRIGGER IF EXISTS update_tasks_updated_at ON tasks')
    op.execute('DROP TRIGGER IF EXISTS update_workflows_updated_at ON workflows')
    op.execute('DROP TRIGGER IF EXISTS update_projects_updated_at ON projects')

    # Drop tables in reverse order
    op.drop_table('tasks')
    op.drop_table('workflows')
    op.drop_table('config_versions')
    op.drop_table('projects')

    # Drop function
    op.execute('DROP FUNCTION IF EXISTS update_updated_at_column()')
```

#### Миграция 002: Add Users and Auth

```python
"""Add users and authentication tables

Revision ID: 002
Revises: 001
Create Date: 2026-03-31 11:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '002'
down_revision = '001'


def upgrade():
    # === users ===
    op.create_table('users',
        sa.Column('id', postgresql.UUID(as_uuid=True),
                  server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('password_hash', sa.String(255), nullable=True),
        sa.Column('email_verified', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('name', sa.String(255), nullable=True),
        sa.Column('avatar_url', sa.String(500), nullable=True),
        sa.Column('role', sa.String(50), nullable=False, server_default='developer'),
        sa.Column('status', sa.String(50), nullable=False, server_default='active'),
        sa.Column('last_login_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('last_login_ip', postgresql.INET(), nullable=True),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()),
                  server_default='{}', nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True),
                  nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True),
                  nullable=False, server_default=sa.text('NOW()')),
        sa.Column('deleted_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email', name='uq_users_email'),
        sa.CheckConstraint(
            "role IN ('admin', 'developer', 'viewer', 'service')",
            name='check_user_role'
        ),
        sa.CheckConstraint(
            "status IN ('active', 'inactive', 'suspended', 'deleted')",
            name='check_user_status'
        ),
        sa.CheckConstraint(
            "email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}$'",
            name='check_email_format'
        )
    )

    # === api_keys ===
    op.create_table('api_keys',
        sa.Column('id', postgresql.UUID(as_uuid=True),
                  server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('key_hash', sa.String(255), nullable=False),
        sa.Column('key_prefix', sa.String(20), nullable=False),
        sa.Column('scopes', postgresql.ARRAY(sa.String()), nullable=False, server_default='{}'),
        sa.Column('expires_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('last_used_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('last_used_ip', postgresql.INET(), nullable=True),
        sa.Column('usage_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('status', sa.String(50), nullable=False, server_default='active'),
        sa.Column('revoked_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('revoked_reason', sa.Text(), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True),
                  nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True),
                  nullable=False, server_default=sa.text('NOW()')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('key_hash', name='uq_api_keys_hash'),
        sa.CheckConstraint(
            "status IN ('active', 'revoked', 'expired')",
            name='check_api_key_status'
        ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    )

    # === user_projects ===
    op.create_table('user_projects',
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('role', sa.String(50), nullable=False, server_default='member'),
        sa.Column('granted_by', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('granted_at', sa.TIMESTAMP(timezone=True),
                  nullable=False, server_default=sa.text('NOW()')),
        sa.PrimaryKeyConstraint('user_id', 'project_id'),
        sa.CheckConstraint(
            "role IN ('owner', 'admin', 'member', 'viewer')",
            name='check_project_role'
        ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['granted_by'], ['users.id'], ondelete='RESTRICT'),
    )

    # === Indexes ===
    op.create_index('idx_users_email', 'users', ['email'])
    op.create_index('idx_users_role', 'users', ['role'])
    op.create_index('idx_users_status', 'users', ['status'])
    op.create_index('idx_users_email_unique', 'users', ['email'],
                    postgresql_where=sa.text('deleted_at IS NULL'))

    op.create_index('idx_api_keys_user_id', 'api_keys', ['user_id'])
    op.create_index('idx_api_keys_key_hash', 'api_keys', ['key_hash'])
    op.create_index('idx_api_keys_key_prefix', 'api_keys', ['key_prefix'])
    op.create_index('idx_api_keys_active', 'api_keys', ['user_id', 'created_at'],
                    postgresql_where=sa.text(
                        "status = 'active' AND (expires_at IS NULL OR expires_at > NOW())"
                    ))

    op.create_index('idx_user_projects_user_id', 'user_projects', ['user_id'])
    op.create_index('idx_user_projects_project_id', 'user_projects', ['project_id'])

    # === Add owner_id FK to projects ===
    op.create_foreign_key(
        'fk_projects_owner_id',
        'projects', 'users',
        ['owner_id'], ['id'],
        ondelete='RESTRICT'
    )

    # === Add created_by FK to config_versions ===
    op.create_foreign_key(
        'fk_config_versions_created_by',
        'config_versions', 'users',
        ['created_by'], ['id'],
        ondelete='SET NULL'
    )


def downgrade():
    # Drop FKs
    op.drop_constraint('fk_projects_owner_id', 'projects', type_='foreignkey')
    op.drop_constraint('fk_config_versions_created_by', 'config_versions', type_='foreignkey')

    # Drop tables
    op.drop_table('user_projects')
    op.drop_table('api_keys')
    op.drop_table('users')
```

#### Миграция 003: Add Agents

```python
"""Add agents table

Revision ID: 003
Revises: 002
Create Date: 2026-03-31 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '003'
down_revision = '002'


def upgrade():
    # === agents ===
    op.create_table('agents',
        sa.Column('id', postgresql.UUID(as_uuid=True),
                  server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('type', sa.String(50), nullable=False),
        sa.Column('model', sa.String(255), nullable=True),
        sa.Column('status', sa.String(50), nullable=False, server_default='idle'),
        sa.Column('current_workflow_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('current_task_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('config', postgresql.JSONB(astext_type=sa.Text()),
                  server_default='{}', nullable=False),
        sa.Column('capabilities', postgresql.ARRAY(sa.String()),
                  nullable=True, server_default='{}'),
        sa.Column('tools', postgresql.ARRAY(sa.String()),
                  nullable=True, server_default='{}'),
        sa.Column('metrics', postgresql.JSONB(astext_type=sa.Text()),
                  server_default='{}', nullable=False),
        sa.Column('last_active_at', sa.TIMESTAMP(timezone=True),
                  server_default=sa.text('NOW()')),
        sa.Column('last_error_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('last_error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True),
                  nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True),
                  nullable=False, server_default=sa.text('NOW()')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name', name='uq_agents_name'),
        sa.CheckConstraint(
            "status IN ('idle', 'busy', 'error', 'offline', 'maintenance')",
            name='check_agent_status'
        ),
        sa.CheckConstraint(
            "type IN ('llm', 'tool', 'hybrid', 'custom')",
            name='check_agent_type'
        ),
        sa.ForeignKeyConstraint(['current_workflow_id'], ['workflows.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['current_task_id'], ['tasks.id'], ondelete='SET NULL'),
    )

    # === Indexes ===
    op.create_index('idx_agents_status', 'agents', ['status'])
    op.create_index('idx_agents_type', 'agents', ['type'])
    op.create_index('idx_agents_model', 'agents', ['model'])
    op.create_index('idx_agents_last_active', 'agents', ['last_active_at'])
    op.create_index('idx_agents_idle', 'agents', ['model', 'last_active_at'],
                    postgresql_where=sa.text("status = 'idle'"))

    # === Add agent_id FK to tasks ===
    op.create_foreign_key(
        'fk_tasks_agent_id',
        'tasks', 'agents',
        ['agent_id'], ['id'],
        ondelete='SET NULL'
    )

    # === Trigger for agent last_active ===
    op.execute("""
        CREATE OR REPLACE FUNCTION update_agent_last_active()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.last_active_at := NOW();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)

    op.execute("""
        CREATE TRIGGER agent_activity_update
        BEFORE UPDATE ON agents
        FOR EACH ROW
        WHEN (OLD.status IS DISTINCT FROM NEW.status
              OR OLD.current_task_id IS DISTINCT FROM NEW.current_task_id)
        EXECUTE FUNCTION update_agent_last_active();
    """)


def downgrade():
    op.execute('DROP TRIGGER IF EXISTS agent_activity_update ON agents')
    op.execute('DROP FUNCTION IF EXISTS update_agent_last_active()')

    op.drop_constraint('fk_tasks_agent_id', 'tasks', type_='foreignkey')
    op.drop_table('agents')
```

#### Миграция 004: Add Budget Tracking

```python
"""Add budget tracking tables

Revision ID: 004
Revises: 003
Create Date: 2026-03-31 13:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '004'
down_revision = '003'


def upgrade():
    # === budget_transactions (partitioned) ===
    op.execute("""
        CREATE TABLE budget_transactions (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
            workflow_id UUID REFERENCES workflows(id) ON DELETE SET NULL,
            task_id UUID REFERENCES tasks(id) ON DELETE SET NULL,
            provider VARCHAR(50) NOT NULL,
            model VARCHAR(255) NOT NULL,
            prompt_tokens INTEGER NOT NULL DEFAULT 0,
            completion_tokens INTEGER NOT NULL DEFAULT 0,
            total_tokens INTEGER NOT NULL DEFAULT 0,
            cost_usd NUMERIC(12, 6) NOT NULL DEFAULT 0,
            cost_per_1k_tokens NUMERIC(10, 6),
            transaction_type VARCHAR(50) NOT NULL DEFAULT 'llm_call',
            metadata JSONB DEFAULT '{}'::jsonb,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT check_transaction_type CHECK (
                transaction_type IN ('llm_call', 'embedding', 'fine_tuning', 'adjustment', 'refund')
            ),
            CONSTRAINT check_tokens_positive CHECK (
                prompt_tokens >= 0 AND completion_tokens >= 0 AND total_tokens >= 0
            ),
            CONSTRAINT check_total_tokens CHECK (total_tokens = prompt_tokens + completion_tokens),
            CONSTRAINT check_cost_positive CHECK (cost_usd >= 0)
        ) PARTITION BY RANGE (created_at)
    """)

    # Create initial partitions
    op.execute("""
        CREATE TABLE budget_transactions_2026_01
        PARTITION OF budget_transactions
        FOR VALUES FROM ('2026-01-01') TO ('2026-02-01')
    """)

    op.execute("""
        CREATE TABLE budget_transactions_2026_02
        PARTITION OF budget_transactions
        FOR VALUES FROM ('2026-02-01') TO ('2026-03-01')
    """)

    op.execute("""
        CREATE TABLE budget_transactions_2026_03
        PARTITION OF budget_transactions
        FOR VALUES FROM ('2026-03-01') TO ('2026-04-01')
    """)

    # Indexes
    op.execute("CREATE INDEX idx_budget_transactions_project ON budget_transactions(project_id)")
    op.execute("CREATE INDEX idx_budget_transactions_workflow ON budget_transactions(workflow_id)")
    op.execute("CREATE INDEX idx_budget_transactions_created_at_brin ON budget_transactions USING BRIN(created_at)")

    # === budget_alerts ===
    op.create_table('budget_alerts',
        sa.Column('id', postgresql.UUID(as_uuid=True),
                  server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('alert_type', sa.String(50), nullable=False),
        sa.Column('threshold', sa.Numeric(10, 4), nullable=False),
        sa.Column('notification_channels', postgresql.ARRAY(sa.String()),
                  nullable=False, server_default='{}'),
        sa.Column('webhook_url', sa.String(500), nullable=True),
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('message_template', sa.Text(), nullable=True),
        sa.Column('last_triggered_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('last_triggered_value', sa.Numeric(10, 4), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True),
                  nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True),
                  nullable=False, server_default=sa.text('NOW()')),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint(
            "alert_type IN ('percentage', 'absolute', 'forecast')",
            name='check_alert_type'
        ),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL'),
    )

    op.create_index('idx_budget_alerts_project', 'budget_alerts', ['project_id'])
    op.create_index('idx_budget_alerts_enabled', 'budget_alerts', ['project_id', 'enabled'],
                    postgresql_where=sa.text('enabled = TRUE'))

    # Trigger for updated_at
    op.execute("""
        CREATE TRIGGER update_budget_alerts_updated_at
        BEFORE UPDATE ON budget_alerts
        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    """)


def downgrade():
    op.execute('DROP TRIGGER IF EXISTS update_budget_alerts_updated_at ON budget_alerts')
    op.drop_table('budget_alerts')
    op.execute('DROP TABLE budget_transactions_2026_03')
    op.execute('DROP TABLE budget_transactions_2026_02')
    op.execute('DROP TABLE budget_transactions_2026_01')
    op.execute('DROP TABLE budget_transactions')
```

#### Миграция 005: Add Audit Logs

```python
"""Add audit logs and events tables

Revision ID: 005
Revises: 004
Create Date: 2026-03-31 14:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '005'
down_revision = '004'


def upgrade():
    # === events (partitioned) ===
    op.execute("""
        CREATE TABLE events (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            event_type VARCHAR(100) NOT NULL,
            category VARCHAR(50) NOT NULL,
            source_type VARCHAR(50) NOT NULL,
            source_id UUID NOT NULL,
            project_id UUID,
            payload JSONB NOT NULL DEFAULT '{}'::jsonb,
            processed BOOLEAN NOT NULL DEFAULT FALSE,
            processed_at TIMESTAMPTZ,
            processed_by VARCHAR(100),
            webhook_deliveries INTEGER NOT NULL DEFAULT 0,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT check_event_category CHECK (
                category IN ('workflow', 'agent', 'budget', 'security', 'config', 'system')
            )
        ) PARTITION BY RANGE (created_at)
    """)

    # Create partitions
    for month in range(1, 7):
        next_month = month + 1 if month < 6 else 1
        year_next = 2026 if month < 6 else 2027
        op.execute(f"""
            CREATE TABLE events_2026_{month:02d}
            PARTITION OF events
            FOR VALUES FROM ('2026-{month:02d}-01') TO ('2026-{next_month:02d}-01')
        """)

    # Indexes
    op.execute("CREATE INDEX idx_events_type ON events(event_type)")
    op.execute("CREATE INDEX idx_events_category ON events(category)")
    op.execute("CREATE INDEX idx_events_created_at_brin ON events USING BRIN(created_at)")
    op.execute("CREATE INDEX idx_events_unprocessed ON events(created_at) WHERE processed = FALSE")

    # === audit_logs (partitioned) ===
    op.execute("""
        CREATE TABLE audit_logs (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID REFERENCES users(id) ON DELETE SET NULL,
            user_email VARCHAR(255),
            user_name VARCHAR(255),
            action VARCHAR(100) NOT NULL,
            resource_type VARCHAR(50) NOT NULL,
            resource_id UUID,
            ip_address INET,
            user_agent TEXT,
            request_id UUID,
            status VARCHAR(50) NOT NULL,
            error_code VARCHAR(100),
            error_message TEXT,
            details JSONB DEFAULT '{}'::jsonb,
            changes JSONB,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT check_audit_status CHECK (
                status IN ('success', 'failure', 'forbidden', 'error')
            ),
            CONSTRAINT check_action_format CHECK (action ~ '^[a-z_]+\\.[a-z_]+$')
        ) PARTITION BY RANGE (created_at)
    """)

    # Create partitions
    for month in range(1, 7):
        op.execute(f"""
            CREATE TABLE audit_logs_2026_{month:02d}
            PARTITION OF audit_logs
            FOR VALUES FROM ('2026-{month:02d}-01') TO ('2026-{month+1:02d}-01')
        """)

    # Indexes
    op.execute("CREATE INDEX idx_audit_logs_user_id ON audit_logs(user_id)")
    op.execute("CREATE INDEX idx_audit_logs_action ON audit_logs(action)")
    op.execute("CREATE INDEX idx_audit_logs_created_at_brin ON audit_logs USING BRIN(created_at)")
    op.execute("CREATE INDEX idx_audit_logs_failures ON audit_logs(created_at) WHERE status IN ('failure', 'forbidden', 'error')")

    # Restrict UPDATE/DELETE on audit_logs
    op.execute("REVOKE UPDATE, DELETE ON audit_logs FROM orchestrator_readwrite")


def downgrade():
    op.execute('DROP TABLE audit_logs_2026_06')
    op.execute('DROP TABLE audit_logs_2026_05')
    op.execute('DROP TABLE audit_logs_2026_04')
    op.execute('DROP TABLE audit_logs_2026_03')
    op.execute('DROP TABLE audit_logs_2026_02')
    op.execute('DROP TABLE audit_logs_2026_01')
    op.execute('DROP TABLE audit_logs')

    op.execute('DROP TABLE events_2026_06')
    op.execute('DROP TABLE events_2026_05')
    op.execute('DROP TABLE events_2026_04')
    op.execute('DROP TABLE events_2026_03')
    op.execute('DROP TABLE events_2026_02')
    op.execute('DROP TABLE events_2026_01')
    op.execute('DROP TABLE events')
```

### 4.3 Rollback Стратегия

```bash
# Проверка статуса миграций
alembic current

# Откат на одну миграцию
alembic downgrade -1

# Откат к конкретной ревизии
alembic downgrade 002

# Откат до чистой базы
alembic downgrade base

# Показать SQL для отката (dry run)
alembic downgrade -1 --sql > rollback.sql

# Важные предупреждения:
# 1. Миграции с удалением данных (DROP TABLE) необратимы
# 2. Всегда делайте backup перед миграцией
# 3. Тестируйте rollback на staging окружении
```

---

## 5. Безопасность Данных

### 5.1 Роли и Доступы

```sql
-- Создание ролей
CREATE ROLE orchestrator_readonly;
CREATE ROLE orchestrator_readwrite;
CREATE ROLE orchestrator_admin;

-- Readonly: только SELECT
GRANT CONNECT ON DATABASE orchestrator TO orchestrator_readonly;
GRANT USAGE ON SCHEMA public TO orchestrator_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO orchestrator_readonly;
GRANT SELECT ON ALL SEQUENCES IN SCHEMA public TO orchestrator_readonly;

-- Readwrite: SELECT, INSERT, UPDATE
GRANT CONNECT ON DATABASE orchestrator TO orchestrator_readwrite;
GRANT USAGE ON SCHEMA public TO orchestrator_readwrite;
GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA public TO orchestrator_readwrite;
GRANT USAGE, SELECT, UPDATE ON ALL SEQUENCES IN SCHEMA public TO orchestrator_readwrite;

-- Admin: полный доступ
GRANT CONNECT ON DATABASE orchestrator TO orchestrator_admin;
GRANT USAGE ON SCHEMA public TO orchestrator_admin;
GRANT ALL ON ALL TABLES IN SCHEMA public TO orchestrator_admin;
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO orchestrator_admin;

-- Будущие таблицы автоматически получают права
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT SELECT ON TABLES TO orchestrator_readonly;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT SELECT, INSERT, UPDATE ON TABLES TO orchestrator_readwrite;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT ALL ON TABLES TO orchestrator_admin;
```

### 5.2 Row Level Security (RLS)

```sql
-- Включение RLS для мультитенантности
ALTER TABLE workflows ENABLE ROW LEVEL SECURITY;
ALTER TABLE tasks ENABLE ROW LEVEL SECURITY;
ALTER TABLE artifacts ENABLE ROW LEVEL SECURITY;
ALTER TABLE budget_transactions ENABLE ROW LEVEL SECURITY;

-- Политика: пользователи видят только свои проекты
CREATE POLICY project_isolation ON workflows
    USING (
        project_id IN (
            SELECT project_id
            FROM user_projects
            WHERE user_id = current_setting('app.current_user_id')::uuid
        )
    );

-- Политика: admin видит всё
CREATE POLICY admin_access ON workflows
    USING (
        current_setting('app.current_user_role') = 'admin'
    );

-- Комбинированная политика
CREATE POLICY workflows_access_policy ON workflows
    USING (
        current_setting('app.current_user_role')::text = 'admin'
        OR project_id IN (
            SELECT project_id FROM user_projects
            WHERE user_id = current_setting('app.current_user_id')::uuid
        )
    );

-- RLS для audit_logs (только admin)
ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY;

CREATE POLICY audit_admin_only ON audit_logs
    USING (current_setting('app.current_user_role')::text = 'admin');
```

### 5.3 Шифрование

```sql
-- Включение pgcrypto для шифрования
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Функция для шифрования секретов
CREATE OR REPLACE FUNCTION encrypt_secret(secret TEXT)
RETURNS BYTEA AS $$
BEGIN
    RETURN pgp_sym_encrypt(secret, current_setting('app.encryption_key'));
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Функция для расшифровки
CREATE OR REPLACE FUNCTION decrypt_secret(encrypted BYTEA)
RETURNS TEXT AS $$
BEGIN
    RETURN pgp_sym_decrypt(encrypted, current_setting('app.encryption_key'));
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Пример использования в таблице
ALTER TABLE webhooks
    ADD COLUMN secret_encrypted BYTEA;

-- Trigger для автоматического шифрования
CREATE OR REPLACE FUNCTION encrypt_webhook_secret()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.secret IS NOT NULL THEN
        NEW.secret_encrypted := encrypt_secret(NEW.secret);
        NEW.secret := NULL;  -- Не храним в открытом виде
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE TRIGGER webhook_secret_encrypt
    BEFORE INSERT OR UPDATE OF secret ON webhooks
    FOR EACH ROW EXECUTE FUNCTION encrypt_webhook_secret();
```

---

## 6. Партиционирование и Архивация

### 6.1 Стратегия Партиционирования

| Таблица                 | Стратегия             | Период  | Причина          |
| ----------------------- | --------------------- | ------- | ---------------- |
| **events**              | RANGE by created_at   | Monthly | 10M+ записей/год |
| **audit_logs**          | RANGE by created_at   | Monthly | 1M+ записей/год  |
| **budget_transactions** | RANGE by created_at   | Monthly | 5M+ записей/год  |
| **webhook_deliveries**  | RANGE by scheduled_at | Monthly | 1M+ записей/год  |

### 6.2 Автоматическое Создание Партиций

```sql
-- Функция для создания будущей партиции
CREATE OR REPLACE FUNCTION create_monthly_partition(
    table_name TEXT,
    partition_date DATE
) RETURNS VOID AS $$
DECLARE
    partition_name TEXT;
    start_date DATE;
    end_date DATE;
BEGIN
    start_date := DATE_TRUNC('month', partition_date);
    end_date := start_date + INTERVAL '1 month';
    partition_name := table_name || '_' || TO_CHAR(start_date, 'YYYY_MM');

    EXECUTE format(
        'CREATE TABLE IF NOT EXISTS %I PARTITION OF %I FOR VALUES FROM (%L) TO (%L)',
        partition_name, table_name, start_date, end_date
    );

    RAISE NOTICE 'Created partition % for table %', partition_name, table_name;
END;
$$ LANGUAGE plpgsql;

-- Создание партиций на 3 месяца вперёд
SELECT create_monthly_partition('events', '2026-04-01');
SELECT create_monthly_partition('events', '2026-05-01');
SELECT create_monthly_partition('events', '2026-06-01');

SELECT create_monthly_partition('audit_logs', '2026-04-01');
SELECT create_monthly_partition('audit_logs', '2026-05-01');
SELECT create_monthly_partition('audit_logs', '2026-06-01');
```

### 6.3 TTL и Удаление Старых Данных

```sql
-- Функция для удаления старых партиций
CREATE OR REPLACE FUNCTION drop_old_partitions(
    table_name TEXT,
    retain_months INTEGER
) RETURNS VOID AS $$
DECLARE
    cutoff_date DATE;
    partition RECORD;
BEGIN
    cutoff_date := DATE_TRUNC('month', NOW() - (retain_months || ' months')::INTERVAL);

    FOR partition IN
        SELECT inhrelid::regclass::TEXT AS partition_name
        FROM pg_inherits
        JOIN pg_class ON pg_inherits.inhparent = pg_class.oid
        WHERE pg_class.relname = table_name
    LOOP
        IF partition.partition_name ~ table_name || '_\d{4}_\d{2}$' THEN
            EXECUTE format(
                'ALTER TABLE %I DETACH PARTITION %I',
                table_name, partition.partition_name
            );
            EXECUTE format('DROP TABLE %I', partition.partition_name);
            RAISE NOTICE 'Dropped old partition %', partition.partition_name;
        END IF;
    END LOOP;
END;
$$ LANGUAGE plpgsql;

-- Удаление данных старше 12 месяцев
SELECT drop_old_partitions('events', 12);
SELECT drop_old_partitions('audit_logs', 12);
SELECT drop_old_partitions('budget_transactions', 24);
```

### 6.4 VACUUM Настройки

```sql
-- Настройки авто-VACUUM для больших таблиц
ALTER TABLE events SET (
    autovacuum_vacuum_scale_factor = 0.01,
    autovacuum_analyze_scale_factor = 0.01,
    autovacuum_vacuum_threshold = 1000,
    autovacuum_analyze_threshold = 1000
);

ALTER TABLE audit_logs SET (
    autovacuum_vacuum_scale_factor = 0.01,
    autovacuum_analyze_scale_factor = 0.01
);

ALTER TABLE budget_transactions SET (
    autovacuum_vacuum_scale_factor = 0.01
);

-- Мониторинг bloat
SELECT
    schemaname,
    relname,
    pg_size_pretty(pg_total_relation_size(relid)) AS total_size,
    pg_size_pretty(pg_relation_size(relid)) AS table_size,
    pg_size_pretty(pg_indexes_size(relid)) AS index_size,
    n_dead_tup,
    n_live_tup,
    ROUND(100.0 * n_dead_tup / NULLIF(n_live_tup + n_dead_tup, 0), 2) AS dead_ratio
FROM pg_stat_user_tables
ORDER BY n_dead_tup DESC;
```

---

## 7. Оценка Размера БД

### 7.1 Прогноз на 1/6/12 месяцев

| Таблица                 | 1 месяц              | 6 месяцев            | 12 месяцев           |
| ----------------------- | -------------------- | -------------------- | -------------------- |
| **users**               | 100 rows / 50 KB     | 500 rows / 250 KB    | 1K rows / 500 KB     |
| **projects**            | 50 rows / 25 KB      | 200 rows / 100 KB    | 500 rows / 250 KB    |
| **workflows**           | 5K rows / 5 MB       | 30K rows / 30 MB     | 60K rows / 60 MB     |
| **tasks**               | 50K rows / 50 MB     | 300K rows / 300 MB   | 600K rows / 600 MB   |
| **budget_transactions** | 100K rows / 50 MB    | 600K rows / 300 MB   | 1.2M rows / 600 MB   |
| **events**              | 500K rows / 250 MB   | 3M rows / 1.5 GB     | 6M rows / 3 GB       |
| **audit_logs**          | 50K rows / 25 MB     | 300K rows / 150 MB   | 600K rows / 300 MB   |
| **Итого**               | ~655K rows / ~380 MB | ~4.2M rows / ~2.3 GB | ~8.4M rows / ~4.6 GB |

### 7.2 Скрипт Генерации Тестовых Данных

```sql
-- Генерация тестовых пользователей
INSERT INTO users (email, name, role, status)
SELECT
    'user' || i || '@example.com',
    'User ' || i,
    (ARRAY['admin', 'developer', 'viewer'])[floor(random() * 3 + 1)],
    'active'
FROM generate_series(1, 100) AS i;

-- Генерация тестовых проектов
INSERT INTO projects (owner_id, name, description, status)
SELECT
    (SELECT id FROM users ORDER BY random() LIMIT 1),
    'Project ' || i,
    'Description for project ' || i,
    (ARRAY['active', 'active', 'active', 'archived'])[floor(random() * 4 + 1)]
FROM generate_series(1, 50) AS i;

-- Генерация конфигов
INSERT INTO config_versions (project_id, version, content, format, created_by, validation_status)
SELECT
    p.id,
    '1.' || i || '.0',
    'version: "1.0"\nproject: "Test"',
    'yaml',
    (SELECT id FROM users ORDER BY random() LIMIT 1),
    'valid'
FROM projects p, generate_series(1, 3) AS i;

-- Генерация workflow
INSERT INTO workflows (project_id, config_version_id, status, priority, total_steps, completed_steps, tokens_used, cost_usd)
SELECT
    p.id,
    (SELECT id FROM config_versions WHERE project_id = p.id ORDER BY random() LIMIT 1),
    (ARRAY['pending', 'queued', 'running', 'completed', 'failed'])[floor(random() * 5 + 1)],
    (ARRAY['low', 'normal', 'high'])[floor(random() * 3 + 1)],
    floor(random() * 10 + 1)::int,
    floor(random() * 5)::int,
    floor(random() * 50000)::int,
    (random() * 10)::numeric(12, 6)
FROM projects p, generate_series(1, 20) AS i;

-- Генерация задач
INSERT INTO tasks (workflow_id, name, step_order, status, tokens_used)
SELECT
    w.id,
    'Task ' || i,
    i,
    (ARRAY['pending', 'running', 'completed', 'failed'])[floor(random() * 4 + 1)],
    floor(random() * 5000)::int
FROM workflows w, generate_series(1, 5) AS i;

-- Генерация транзакций бюджета
INSERT INTO budget_transactions (project_id, workflow_id, provider, model, total_tokens, cost_usd, created_at)
SELECT
    w.project_id,
    w.id,
    (ARRAY['openai', 'anthropic', 'azure'])[floor(random() * 3 + 1)],
    (ARRAY['gpt-4', 'gpt-3.5-turbo', 'claude-3-opus', 'claude-3-sonnet'])[floor(random() * 4 + 1)],
    floor(random() * 10000)::int,
    (random() * 0.5)::numeric(12, 6),
    NOW() - (random() * INTERVAL '30 days')
FROM workflows w, generate_series(1, 10) AS i;
```

---

**Конец документации схемы БД**
