# AFL Orchestrator - Repository Setup Guide

This guide covers Git repository configuration, branch strategy, and development
workflow.

---

## Quick Start

```bash
# 1. Clone the repository
git clone <repository-url>
cd afl-orc

# 2. Run the setup script
./scripts/setup-git.sh

# 3. Activate virtual environment
source .venv/bin/activate

# 4. Create your feature branch
git checkout -b feature/YOUR-TICKET-description

# 5. Start coding!
```

---

## Repository Structure

```
afl-orc/
├── .git/                    # Git repository
├── .github/
│   ├── workflows/
│   │   └── ci-cd.yml       # CI/CD pipeline
│   ├── ISSUE_TEMPLATE/
│   │   └── config.yml      # Issue templates
│   └── PULL_REQUEST_TEMPLATE.md
├── .gitignore              # Git ignore rules
├── .pre-commit-config.yaml # Pre-commit hooks
├── .sqlfluff              # SQL linting config
├── pyproject.toml         # Python project config
├── scripts/
│   └── setup-git.sh       # Setup script
├── src/
│   └── orchestrator/      # Source code
├── tests/
│   ├── unit/
│   ├── integration/
│   └── e2e/
└── docs/
```

---

## Git Flow

### Branch Strategy

```
main (production)
  └── develop (integration)
        ├── feature/*
        ├── bugfix/*
        ├── hotfix/*
        └── release/*
```

### Branch Naming

| Type    | Pattern                      | Example                      |
| ------- | ---------------------------- | ---------------------------- |
| Feature | `feature/TICKET-description` | `feature/AFL-101-add-parser` |
| Bugfix  | `bugfix/TICKET-description`  | `bugfix/AFL-205-fix-state`   |
| Hotfix  | `hotfix/TICKET-description`  | `hotfix/AFL-301-critical`    |
| Release | `release/vX.Y.Z`             | `release/v1.0.0`             |

### Workflow Summary

```bash
# Start feature
git checkout develop
git checkout -b feature/AFL-XXX-desc

# Daily work
git add .
git commit -m "type(scope): description"
git push

# Sync with develop
git fetch origin
git rebase origin/develop

# After PR merge
git checkout develop && git pull
git branch -d feature/AFL-XXX-desc
```

---

## Pre-commit Hooks

### Installation

```bash
# Install pre-commit
pip install pre-commit

# Install git hooks
pre-commit install
```

### Enabled Hooks

| Hook                   | Purpose                       |
| ---------------------- | ----------------------------- |
| trailing-whitespace    | Remove trailing whitespace    |
| end-of-file-fixer      | Ensure file ends with newline |
| check-yaml             | Validate YAML syntax          |
| check-json             | Validate JSON syntax          |
| detect-private-key     | Detect private keys           |
| detect-aws-credentials | Detect AWS credentials        |
| isort                  | Sort Python imports           |
| black                  | Format Python code            |
| ruff                   | Lint Python code              |
| mypy                   | Type checking                 |
| bandit                 | Security scanning             |
| sqlfluff               | SQL linting                   |

### Manual Run

```bash
# Run all hooks
pre-commit run --all-files

# Run specific hook
pre-commit run black --all-files
```

---

## Commit Message Convention

We use [Conventional Commits](https://www.conventionalcommits.org/):

```
type(scope): description

[optional body]

[optional footer]
```

### Types

| Type       | Description   |
| ---------- | ------------- |
| `feat`     | New feature   |
| `fix`      | Bug fix       |
| `docs`     | Documentation |
| `style`    | Code style    |
| `refactor` | Refactoring   |
| `test`     | Tests         |
| `chore`    | Maintenance   |

### Examples

```bash
feat(parser): add YAML parsing with anchor support

Implemented full YAML 1.2 parsing with support for:
- Anchors and aliases
- Multi-line strings

Closes AFL-101

fix(workflow): resolve state machine deadlock

The workflow engine could deadlock when transitioning
from PAUSED to RUNNING.

Fixes AFL-205

test(budget): add integration tests for budget tracking

Added 15 test cases covering token accounting.

Refs AFL-150
```

---

## CI/CD Pipeline

### Triggers

| Event        | Branches                       | Actions              |
| ------------ | ------------------------------ | -------------------- |
| Push         | `main`, `develop`, `feature/*` | Lint, Test, Security |
| Pull Request | `main`, `develop`              | Full pipe-line       |
| Tag          | `v*`                           | Release              |

### Pipe-line Stages

```
1. Lint & Type Check
   ├── Pre-commit hooks
   └── MyPy

2. Unit Tests
   ├── PostgreSQL
   ├── Redis
   └── Coverage report

3. Integration Tests
   ├── PostgreSQL
   ├── Redis
   ├── MinIO
   └── Coverage report

4. Security Scan
   ├── Bandit
   ├── Safety
   └── Pip Audit

5. Build Docker
   └── Build & test image

6. Deploy Staging (develop)
   └── Deploy to staging

7. Deploy Production (main/tag)
   └── Deploy to production

8. Create Release (tag)
   └── GitHub release
```

---

## Configuration Files

### `.pre-commit-config.yaml`

Pre-commit hooks configuration. See file for details.

### `pyproject.toml`

Python project configuration:

- `[tool.isort]` - Import sorting
- `[tool.black]` - Code formatting
- `[tool.ruff]` - Linting
- `[tool.mypy]` - Type checking
- `[tool.pytest]` - Test configuration
- `[tool.coverage]` - Coverage settings

### `.sqlfluff`

SQL linting configuration for PostgreSQL dialect.

### `.gitignore`

Ignores:

- Python cache (`__pycache__/`)
- Virtual environments (`.venv/`)
- IDE files (`.idea/`, `.vscode/`)
- Secrets and credentials
- Build artifacts

---

## Development Workflow

### 1. Setup

```bash
./scripts/setup-git.sh
source .venv/bin/activate
```

### 2. Create Feature Branch

```bash
git checkout develop
git pull origin develop
git checkout -b feature/AFL-XXX-description
```

### 3. Develop

```bash
# Make changes
git add .

# Commit with conventional format
git commit -m "feat(parser): add YAML support"

# Push
git push -u origin feature/AFL-XXX-description
```

### 4. Create Pull Request

1. Go to GitHub
2. Create PR: `feature/AFL-XXX` → `develop`
3. Fill PR template
4. Request review
5. Address comments
6. Merge (squash)

### 5. Clean Up

```bash
git checkout develop
git pull origin develop
git branch -d feature/AFL-XXX-description
git push origin --delete feature/AFL-XXX-description
```

---

## Useful Commands

### Git

```bash
# View branch structure
git branch -a

# View commit history
git log --oneline --graph --all

# Stash changes
git stash
git stash pop

# Rebase interactively
git rebase -i HEAD~3

# View diff
git diff develop
```

### Pre-commit

```bash
# Run all hooks
pre-commit run --all-files

# Run on specific files
pre-commit run black --files src/parser.py

# Update hooks
pre-commit autoupdate

# Uninstall hooks
pre-commit uninstall
```

### Testing

```bash
# Run all tests
pytest

# Run specific test
pytest tests/unit/test_parser.py -v

# Run with coverage
pytest --cov=src --cov-report=html

# Run by marker
pytest -m unit
pytest -m integration
pytest -m "not slow"
```

### Linting

```bash
# Run ruff
ruff check src/

# Run black
black src/ --check

# Run mypy
mypy src/

# Run sqlfluff
sqlfluff lint migrations/ --dialect postgres
```

---

## Troubleshooting

### Pre-commit Fails

```bash
# See what hooks will run
pre-commit run --verbose --all-files

# Run hook in debug mode
pre-commit run black --verbose
```

### Merge Conflicts

```bash
# Start rebase
git rebase origin/develop

# Resolve conflicts, then
git add <resolved-files>
git rebase --continue
```

### Accidental Commit to Wrong Branch

```bash
# Create correct branch
git checkout -b feature/correct-branch

# Cherry-pick commit
git cherry-pick <commit-hash>

# Reset wrong branch
git checkout wrong-branch
git reset --hard HEAD~1
```

---

## Resources

- [Git Flow](https://nvie.com/posts/a-successful-git-branching-model/)
- [Conventional Commits](https://www.conventionalcommits.org/)
- [Pre-commit](https://pre-commit.com/)
- [GitHub Actions](https://docs.github.com/en/actions)

---

## Support

For questions or issues:

- Check existing issues in GitHub
- Contact: dev-team@afl-orchestrator.com
- Documentation: See `docs/` folder
