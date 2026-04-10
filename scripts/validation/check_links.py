#!/usr/bin/env python3
"""
Проверка Markdown ссылок на битые референсы.
"""

import re
from pathlib import Path
from typing import Dict, List
import time

def check_markdown_links(docs_dir: Path) -> Dict:
    """Проверяет все Markdown ссылки в документах."""
    start_time = time.time()
    issues = []
    warnings = []
    
    # Паттерны для ссылок
    link_pattern = re.compile(r'\[([^\]]+)\]\(([^\)]+)\)')
    ref_pattern = re.compile(r'\[([^\]]+)\]\[([^\]]*)\]')
    
    all_files = list(docs_dir.glob("*.md"))
    all_anchors = {}  # file -> [anchors]
    
    ANCHOR_TRANSLATE_TABLE = str.maketrans(" ", "-", ",.()")
    # Сначала собираем все якоря (заголовки)
    for file_path in all_files:
        anchors = []
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
            # Извлекаем заголовки как якоря
            headers = re.findall(r'^#{1,6}\s+(.+)$', content, re.MULTILINE)
            for header in headers:
                anchor = header.lower().translate(ANCHOR_TRANSLATE_TABLE)
                anchors.append(f"#{anchor}")
        all_anchors[file_path.name] = anchors
    
    # Проверяем ссылки
    for file_path in all_files:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
            lines = content.split("\n")
            
            for line_num, line in enumerate(lines, 1):
                # Пропускаем код блоки
                if "```" in line:
                    continue
                    
                matches = link_pattern.findall(line)
                for text, url in matches:
                    # Внешние ссылки пропускаем
                    if url.startswith("http"):
                        continue
                    
                    # Проверка внутренних ссылок
                    if url.startswith("#"):
                        # Якорь в том же файле
                        if url not in all_anchors.get(file_path.name, []):
                            issues.append({
                                "file": str(file_path),
                                "line": line_num,
                                "type": "broken_anchor",
                                "message": f"Broken anchor link: {url}",
                                "context": line.strip()[:100]
                            })
                    elif ".md" in url:
                        # Ссылка на файл
                        target_file = docs_dir / url.split("#")[0]
                        if not target_file.exists():
                            issues.append({
                                "file": str(file_path),
                                "line": line_num,
                                "type": "broken_file_link",
                                "message": f"File not found: {url}",
                                "context": line.strip()[:100]
                            })
    
    duration = time.time() - start_time
    
    return {
        "success": len(issues) == 0,
        "issues": issues,
        "warnings": warnings,
        "duration": round(duration, 2),
        "files_checked": len(all_files)
    }