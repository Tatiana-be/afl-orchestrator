#!/usr/bin/env python3
"""
Проверка консистентности терминологии across документов.
"""
import re
from pathlib import Path
from typing import Dict
from collections import defaultdict
import time

# Термины и их предпочтительные формы
TERMINOLOGY_RULES = {
    "workflow": ["pipeline", "flow", "process"],
    "project_id": ["projectId", "proj_id", "projectid"],
    "user_id": ["userId", "usr_id"],
    "API": ["Api", "api"],
    "UUID": ["uuid", "Uid"],
    "PostgreSQL": ["postgres", "Postgres"],
    "JSON": ["json", "Json"],
    "GitHub": ["github", "Github"],
    "Docker": ["docker"],
    "Kubernetes": ["k8s", "kubernetes"],
}

# 🔹 Устоявшиеся фразы, которые нужно пропускать
EXCLUDED_PHRASES = [
    "Pipeline Pattern", "Agentic Flow", "Git Flow",
    "CI/CD Pipeline", "Validator Pipeline",
    "Release Process", "Build process"
]

# Компилируем паттерн один раз для максимальной производительности
EXCLUDED_PATTERN = re.compile(
    r'(' + '|'.join(re.escape(p) for p in EXCLUDED_PHRASES) + r')',
    re.IGNORECASE
)

def check_terminology_consistency(docs_dir: Path) -> Dict:
    """Проверяет использование терминов в документах."""
    start_time = time.time()
    issues = []
    warnings = []
    all_files = list(docs_dir.glob("*.md"))
    term_occurrences = defaultdict(list)  # term -> [{file, line, variant}]

    for file_path in all_files:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        lines = content.splitlines()
        inside_code_block = False  # Состояние: внутри ``` ... ```

        for line_num, line in enumerate(lines, 1):
            stripped = line.strip()

            # 1️⃣ Отслеживаем блоки кода
            if stripped.startswith("```"):
                inside_code_block = not inside_code_block
                continue  # Саму строку-ограничитель не анализируем
            if inside_code_block:
                continue

            # 2️⃣ Пропускаем строки, содержащие устоявшиеся фразы
            if EXCLUDED_PATTERN.search(line):
                continue

            # 3️⃣ Анализируем терминологию только в чистом тексте
            for preferred, variants in TERMINOLOGY_RULES.items():
                # Ищем предпочтительную форму
                if re.search(r'\b' + re.escape(preferred) + r'\b', line, re.IGNORECASE):
                    term_occurrences[preferred].append({
                        "file": str(file_path),
                        "line": line_num,
                        "variant": preferred
                    })
                
                # Ищем нежелательные варианты
                for variant in variants:
                    if re.search(r'\b' + re.escape(variant) + r'\b', line, re.IGNORECASE):
                        if variant.lower() != preferred.lower():
                            issues.append({
                                "file": str(file_path),
                                "line": line_num,
                                "type": "terminology_inconsistency",
                                "message": f"Inconsistent terminology: '{variant}' should be '{preferred}'",
                                "context": line.strip()[:100],
                                "recommended": preferred
                            })

    # ⚠️ Warnings генерируем один раз после обхода всех файлов
    for term, occurrences in term_occurrences.items():
        if len(occurrences) < 3:
            warnings.append({
                "type": "rare_term",
                "message": f"Term '{term}' used only {len(occurrences)} times — check if it's needed",
                "occurrences": len(occurrences)
            })

    duration = time.time() - start_time
    return {
        "success": len(issues) == 0,
        "issues": issues,
        "warnings": warnings,
        "duration": round(duration, 2),
        "files_checked": len(all_files),
        "terms_found": len(term_occurrences)
    }