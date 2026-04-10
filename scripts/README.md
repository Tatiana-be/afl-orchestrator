# 📜 AFL Orchestrator Documentation Validation Scripts

Автоматическая валидация документации на консистентность и ошибки.

## 🚀 Быстрый старт

```bash
# 1. Установка зависимостей
pip install -r scripts/requirements.txt

# 2. Запуск всех проверок
python scripts/validation/run_all_checks.py --docs-dir ./documentation --output ./reports

# 3. Открыть отчёт
open reports/validation_report.html
```

## 📊 Выходные данные

| Файл | Описание |
|------|----------|
| `reports/validation_results.json` | JSON с результатами всех проверок |
| `reports/validation_report.html` | Визуальный HTML отчёт |
| `reports/consistency_matrix.csv` | Матрица кросс-документ консистентности |

## 🔧 Настройка

Отредактируйте `config/validation_config.yaml` для:
- Добавления новых терминов
- Изменения порогов
- Исключения файлов

## 🔄 CI/CD Интеграция

### GitHub Actions
```yaml
- name: Validate Documentation
  run: |
    pip install -r scripts/requirements.txt
    python scripts/validation/run_all_checks.py --fail-on-warning
```

### GitLab CI
```yaml
validate_docs:
  script:
    - pip install -r scripts/requirements.txt
    - python scripts/validation/run_all_checks.py
  artifacts:
    paths:
      - reports/
```

## 📈 Интерпретация результатов

| Статус | Значение | Действие |
|--------|----------|----------|
| ✅ PASSED | Все проверки пройдены | Можно начинать ручное ревью |
| ⚠️ WARNING | Есть предупреждения | Исправить до начала разработки |
| ❌ FAILED | Критичные ошибки | Блокирует дальнейшую работу |

## 🐛 Troubleshooting

**Ошибка: `ModuleNotFoundError`**
```bash
pip install -r scripts/requirements.txt --upgrade
```

**Ошибка: `Documentation directory not found`**
```bash
# Проверьте путь
ls -la documentation/
```

**Ложные срабатывания терминологии**
```yaml
# Добавьте исключение в config/validation_config.yaml
terminology:
  exclusions:
    - "legacy_api"  # Этот термин разрешён в историческом контексте
```