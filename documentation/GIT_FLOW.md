# Git Flow Configuration for AFL Orchestrator

## Branch Strategy

We use a modified Git Flow workflow optimized for AI/ML projects with frequent
iterations.

### Branch Types

```
main
  └── develop
        ├── feature/*
        ├── bugfix/*
        ├── hotfix/*
        └── release/*
```

### Branch Descriptions

| Branch      | Pattern                      | Purpose                              | Protected          |
| ----------- | ---------------------------- | ------------------------------------ | ------------------ |
| **Main**    | `main`                       | Production-ready code, auto-deployed | ✅ Yes             |
| **Develop** | `develop`                    | Integration branch for features      | ✅ Yes             |
| **Feature** | `feature/TICKET-description` | New features                         | ❌ No              |
| **Bugfix**  | `bugfix/TICKET-description`  | Bug fixes for develop                | ❌ No              |
| **Hotfix**  | `hotfix/TICKET-description`  | Critical production fixes            | ⚠️ Review required |
| **Release** | `release/vX.Y.Z`             | Release preparation                  | ✅ Yes             |

---

## Branch Naming Conventions

### Format

```
{type}/{ticket-id}-{short-description}
```

### Examples

```
feature/AFL-101-add-parser-module
bugfix/AFL-205-fix-workflow-state-machine
hotfix/AFL-301-critical-budget-tracking-fix
release/v1.0.0-mvp
```

### Types

- `feature` - New functionality
- `bugfix` - Bug fixes
- `hotfix` - Critical production fixes
- `release` - Release branches
- `chore` - Maintenance tasks (optional)
- `docs` - Documentation only (optional)
- `test` - Test additions/fixes (optional)

---

## Workflow

### 1. Starting a New Feature

```bash
# Ensure you're on develop with latest changes
git checkout develop
git pull origin develop

# Create feature branch
git checkout -b feature/AFL-101-add-parser-module

# Work on your feature...
git add .
git commit -m "feat: implement AFL parser with Pydantic validation

- Add YAML/JSON parsing support
- Implement schema validation
- Add error handling with line/column info

Closes AFL-101"

# Push feature branch
git push -u origin feature/AFL-101-add-parser-module
```

### 2. Creating a Pull Request

1. Go to GitHub/GitLab
2. Create PR from `feature/AFL-101-add-parser-module` → `develop`
3. Fill PR template
4. Request review from team members
5. Address review comments
6. Squash and merge when approved

### 3. Completing a Feature

```bash
# After PR is merged, clean up locally
git checkout develop
git pull origin develop
git branch -d feature/AFL-101-add-parser-module

# Clean up remote branch (if not auto-deleted)
git push origin --delete feature/AFL-101-add-parser-module
```

### 4. Hotfix Workflow

```bash
# Branch from main
git checkout main
git pull origin main
git checkout -b hotfix/AFL-301-critical-fix

# Make fixes
git commit -m "fix: critical budget tracking issue

- Fix race condition in budget updates
- Add transaction locking

Fixes AFL-301"

# Push and create PR to main
git push -u origin hotfix/AFL-301-critical-fix

# After merge, also merge to develop
git checkout develop
git merge main
git push origin develop
```

### 5. Release Process

```bash
# Create release branch from develop
git checkout develop
git pull origin develop
git checkout -b release/v1.0.0-mvp

# Update version numbers, changelog
# Run final tests
# Fix any last-minute issues

git commit -m "chore: bump version to 1.0.0"

# Push and create PR to main
git push -u origin release/v1.0.0-mvp

# After approval, merge to main AND develop
# Tag the release
git checkout main
git pull origin main
git tag -a v1.0.0 -m "Release v1.0.0 - MVP"
git push origin v1.0.0
```

---

## Commit Message Convention

We use [Conventional Commits](https://www.conventionalcommits.org/) format.

### Format

```
{type}({scope}): {description}

[optional body]

[optional footer]
```

### Types

- `feat` - New feature
- `fix` - Bug fix
- `docs` - Documentation only
- `style` - Code style (formatting, semicolons, etc.)
- `refactor` - Code change that neither fixes a bug nor adds a feature
- `test` - Adding or fixing tests
- `chore` - Build process, tooling, etc.

### Examples

```
feat(parser): add YAML parsing with anchor support

Implemented full YAML 1.2 parsing with support for:
- Anchors and aliases
- Multi-line strings
- Custom tags

Closes AFL-101

fix(workflow): resolve state machine deadlock

The workflow engine could deadlock when transitioning
from PAUSED to RUNNING with concurrent step completion.

Fixes AFL-205

docs(api): update workflow endpoint documentation

Added examples for all workflow endpoints and error responses.

test(budget): add integration tests for budget tracking

Added 15 test cases covering:
- Token accounting accuracy
- Budget limit enforcement
- Alert triggering

Refs AFL-150
```

---

## Pre-commit Hooks

Install pre-commit hooks before starting development:

```bash
# Install pre-commit
pip install pre-commit

# Install git hooks
pre-commit install

# (Optional) Install for all repositories
pre-commit install --install-hooks

# Run manually
pre-commit run --all-files
```

### Hooks Enabled

- ✅ Trailing whitespace removal
- ✅ End of file fixer
- ✅ YAML/JSON/TOML validation
- ✅ Merge conflict detection
- ✅ Private key detection
- ✅ AWS credentials detection
- ✅ Python import sorting (isort)
- ✅ Python formatting (Black)
- ✅ Python linting (Ruff)
- ✅ Type checking (MyPy)
- ✅ Security scanning (Bandit)
- ✅ Secret detection (detect-secrets)
- ✅ SQL linting (SQLFluff)
- ✅ Markdown formatting (Prettier)

---

## Protection Rules

### Main Branch (`main`)

- ✅ Require pull request reviews (minimum 1)
- ✅ Require status checks to pass
- ✅ Require branches to be up to date before merging
- ✅ Require conversation resolution
- ✅ Include administrators
- ✅ Restrict pushes (no direct commits)

### Develop Branch (`develop`)

- ✅ Require pull request reviews (minimum 1)
- ✅ Require status checks to pass
- ⚠️ Allow force pushes (for rebasing)

### Release Branches (`release/*`)

- ✅ Require pull request reviews
- ✅ Require status checks to pass
- ✅ Restrict deletion (keep for history)

---

## Version Tagging

We use [Semantic Versioning](https://semver.org/):

```
MAJOR.MINOR.PATCH
```

- **MAJOR** - Breaking changes
- **MINOR** - New features (backward compatible)
- **PATCH** - Bug fixes (backward compatible)

### Tag Examples

```bash
# Regular release
git tag -a v1.0.0 -m "Release v1.0.0"

# Pre-release
git tag -a v1.0.0-beta.1 -m "Beta release 1"
git tag -a v1.0.0-rc.1 -m "Release candidate 1"

# Push tags
git push origin v1.0.0
git push origin --tags
```

---

## CI/CD Integration

### GitHub Actions Workflow Triggers

```yaml
# On feature branch push
on:
  push:
    branches:
      - 'feature/*'
      - 'bugfix/*'

# On PR to develop/main
on:
  pull_request:
    branches:
      - 'develop'
      - 'main'

# On release
on:
  push:
    tags:
      - 'v*'
```

### Status Checks Required

- ✅ Unit tests pass
- ✅ Integration tests pass
- ✅ Linting passes
- ✅ Type checking passes
- ✅ Security scan passes
- ✅ Code coverage > 80%

---

## Quick Reference

```bash
# Start new feature
git checkout develop && git pull
git checkout -b feature/AFL-XXX-description

# Daily work
git add .
git commit -m "type(scope): description"
git push

# Sync with develop
git fetch origin
git rebase origin/develop

# Prepare for PR
pre-commit run --all-files
pytest --cov=src tests/

# After PR merge
git checkout develop && git pull
git branch -d feature/AFL-XXX-description
git push origin --delete feature/AFL-XXX-description

# Hotfix
git checkout main && git pull
git checkout -b hotfix/AFL-XXX-critical-fix
# ... fix, commit, PR to main ...
git checkout develop && git merge main
```

---

## Troubleshooting

### Accidentally committed to wrong branch

```bash
# If you committed to main instead of feature branch
git checkout -b feature/correct-branch
git cherry-pick <commit-hash>
git checkout main
git reset --hard HEAD~1
git push origin feature/correct-branch
git push origin main --force  # Be careful!
```

### Resolve merge conflicts

```bash
git merge origin/develop
# Edit conflicted files
git add <resolved-files>
git commit  # Complete merge
```

### Undo last commit (keep changes)

```bash
git reset --soft HEAD~1
```

### Undo last commit (discard changes)

```bash
git reset --hard HEAD~1
```
