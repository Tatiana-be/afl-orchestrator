#!/usr/bin/env python3
"""
Проверка SQL синтаксиса в документации.
"""

import re
from pathlib import Path
from typing import Dict, List
import time

def check_sql_syntax(docs_dir: Path) -> Dict:
    """Проверяет SQL блоки в документации."""
    start_time = time.time()
    issues = []
    warnings = []
    
    all_files = list(docs_dir.glob("*.md"))
    
    # Базовые проверки SQL
    sql_keywords = ["CREATE", "TABLE", "PRIMARY", "KEY", "FOREIGN", "REFERENCES", 
                    "INDEX", "INSERT", "SELECT", "UPDATE", "DELETE", "ALTER"]
    
    for file_path in all_files:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
            
            # Извлекаем SQL блоки
            sql_blocks = re.findall(r'```sql\s*(.*?)```', content, re.DOTALL | re.IGNORECASE)
            
            for block_num, sql in enumerate(sql_blocks, 1):
                lines = sql.strip().split("\n")
                
                # Проверка 1: CREATE TABLE должен иметь имя
                for line in lines:
                    if "CREATE TABLE" in line.upper():
                        if not re.search(r'CREATE TABLE\s+\w+', line, re.IGNORECASE):
                            issues.append({
                                "file": str(file_path),
                                "block": block_num,
                                "type": "sql_syntax",
                                "message": "CREATE TABLE without table name"
                            })
                
                # Проверка 2: PRIMARY KEY должен быть определён
                has_create = any("CREATE TABLE" in l.upper() for l in lines)
                has_pk = any("PRIMARY KEY" in l.upper() for l in lines) or any("SERIAL" in l.upper() for l in lines)
                
                if has_create and not has_pk:
                    warnings.append({
                        "file": str(file_path),
                        "block": block_num,
                        "type": "sql_warning",
                        "message": "CREATE TABLE without PRIMARY KEY"
                    })
                
                # Проверка 3: Несбалансированные скобки
                open_parens = sql.count("(")
                close_parens = sql.count(")")
                if open_parens != close_parens:
                    issues.append({
                        "file": str(file_path),
                        "block": block_num,
                        "type": "sql_syntax",
                        "message": f"Unbalanced parentheses: {open_parens} open, {close_parens} close"
                    })
    
    duration = time.time() - start_time
    
    return {
        "success": len(issues) == 0,
        "issues": issues,
        "warnings": warnings,
        "duration": round(duration, 2),
        "files_checked": len(all_files)
    }