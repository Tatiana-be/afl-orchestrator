#!/usr/bin/env python3
"""
Проверка корректности Markdown таблиц.
"""

import re
from pathlib import Path
from typing import Dict, List
import time

def check_markdown_tables(docs_dir: Path) -> Dict:
    """Проверяет синтаксис Markdown таблиц."""
    start_time = time.time()
    issues = []
    warnings = []
    
    all_files = list(docs_dir.glob("*.md"))
    
    for file_path in all_files:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
            lines = content.split("\n")
            
            in_table = False
            table_start_line = 0
            column_count = 0
            
            for line_num, line in enumerate(lines, 1):
                # Начало таблицы
                if re.match(r'^\|.*\|', line) and not in_table:
                    in_table = True
                    table_start_line = line_num
                    column_count = line.count("|") - 1
                    
                # Разделитель таблицы
                elif in_table and re.match(r'^\|[\s\-:|]+\|', line):
                    separator_cols = line.count("|") - 1
                    if separator_cols != column_count:
                        issues.append({
                            "file": str(file_path),
                            "line": line_num,
                            "type": "table_mismatch",
                            "message": f"Table separator column count ({separator_cols}) doesn't match header ({column_count})"
                        })
                
                # Строка таблицы
                elif in_table and re.match(r'^\|.*\|', line):
                    current_cols = line.count("|") - 1
                    if current_cols != column_count:
                        issues.append({
                            "file": str(file_path),
                            "line": line_num,
                            "type": "table_mismatch",
                            "message": f"Table row column count ({current_cols}) doesn't match header ({column_count})"
                        })
                
                # Конец таблицы
                elif in_table and not re.match(r'^\|.*\|', line) and line.strip():
                    in_table = False
    
    duration = time.time() - start_time
    
    return {
        "success": len(issues) == 0,
        "issues": issues,
        "warnings": warnings,
        "duration": round(duration, 2),
        "files_checked": len(all_files)
    }