#!/usr/bin/env python3
"""
Проверка консистентности между документами (сущности, версии, ID).
"""

import re
from pathlib import Path
from typing import Dict, List
from collections import defaultdict
import time
import json

def extract_entities(content: str) -> Dict:
    """Извлекает сущности из документа."""
    entities = {
        "api_endpoints": [],
        "table_names": [],
        "field_names": [],
        "versions": [],
        "status_values": []
    }
    
    # API эндпоинты
    endpoints = re.findall(r'(GET|POST|PUT|DELETE|PATCH)\s+(/api/[^`\s]+)', content)
    entities["api_endpoints"] = [f"{method} {path}" for method, path in endpoints]
    
    # Таблицы БД
    tables = re.findall(r'CREATE TABLE\s+(\w+)', content, re.IGNORECASE)
    entities["table_names"] = tables
    
    # Поля
    fields = re.findall(r'(\w+_id|\w+Id)\s*:', content)
    entities["field_names"] = list(set(fields))
    
    # Версии
    versions = re.findall(r'v\d+\.\d+[^.]', content)
    entities["versions"] = list(set(versions))
    
    # Статусы
    statuses = re.findall(r"'(pending|running|completed|failed|cancelled)'", content)
    entities["status_values"] = list(set(statuses))
    
    return entities


def check_cross_document_consistency(docs_dir: Path) -> Dict:
    """Проверяет консистентность между документами."""
    start_time = time.time()
    issues = []
    warnings = []
    
    all_files = list(docs_dir.glob("*.md"))
    all_entities = {}  # file -> entities
    
    # Извлекаем сущности из всех файлов
    for file_path in all_files:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
            all_entities[file_path.name] = extract_entities(content)
    
    # Сравниваем API эндпоинты между API_SPEC и другими документами
    api_files = [f for f in all_entities.keys() if "API" in f.upper()]
    other_files = [f for f in all_entities.keys() if "API" not in f.upper()]
    
    all_endpoints = set()
    for file, entities in all_entities.items():
        all_endpoints.update(entities.get("api_endpoints", []))
    
    # Проверка версий
    all_versions = set()
    for file, entities in all_entities.items():
        all_versions.update(entities.get("versions", []))
    
    if len(all_versions) > 1:
        issues.append({
            "type": "version_mismatch",
            "message": f"Multiple API versions found: {', '.join(all_versions)}",
            "recommendation": "Use consistent versioning across all documents"
        })
    
    # Проверка статусов
    all_statuses = set()
    for file, entities in all_entities.items():
        all_statuses.update(entities.get("status_values", []))
    
    expected_statuses = {"pending", "running", "completed", "failed", "cancelled"}
    if all_statuses and not all_statuses.issubset(expected_statuses):
        unexpected = all_statuses - expected_statuses
        warnings.append({
            "type": "unexpected_status",
            "message": f"Unexpected status values found: {unexpected}",
            "expected": list(expected_statuses)
        })
    
    # Проверка naming convention (snake_case vs camelCase)
    all_fields = []
    for file, entities in all_entities.items():
        all_fields.extend(entities.get("field_names", []))
    all_fields.remove("operationId")  # ID from YAML
    
    snake_case = [f for f in all_fields if "_" in f]
    camel_case = [f for f in all_fields if "_" not in f and any(c.isupper() for c in f)]
    
    if camel_case and snake_case:
        issues.append({
            "type": "naming_inconsistency",
            "message": f"Mixed naming conventions: snake_case ({len(snake_case)}: {snake_case}) and camelCase ({len(camel_case)}: {camel_case})",
            "recommendation": "Use snake_case consistently for database fields"
        })
    
    duration = time.time() - start_time
    
    return {
        "success": len(issues) == 0,
        "issues": issues,
        "warnings": warnings,
        "duration": round(duration, 2),
        "files_checked": len(all_files),
        "endpoints_found": len(all_endpoints),
        "versions_found": list(all_versions)
    }