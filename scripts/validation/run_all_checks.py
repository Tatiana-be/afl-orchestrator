#!/usr/bin/env python3
"""
AFL Orchestrator Documentation Pre-Validation Runner
Запускает все проверки и генерирует сводный отчёт.

Usage:
    python scripts/validation/run_all_checks.py --docs-dir ./documentation --output ./reports
"""

import argparse
import sys
import os
from datetime import datetime
from pathlib import Path

# Импорт модулей проверок
from check_links import check_markdown_links
from check_terminology import check_terminology_consistency
from check_consistency import check_cross_document_consistency
from check_tables import check_markdown_tables
from check_schema_syntax import check_sql_syntax

# Конфигурация
DEFAULT_DOCS_DIR = "./documentation"
DEFAULT_OUTPUT_DIR = "./reports"

class ValidationRunner:
    def __init__(self, docs_dir: str, output_dir: str):
        self.docs_dir = Path(docs_dir)
        self.output_dir = Path(output_dir)
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "checks": [],
            "summary": {
                "total": 0,
                "passed": 0,
                "failed": 0,
                "warnings": 0
            }
        }
        
    def run_check(self, name: str, check_func, **kwargs):
        """Запускает отдельную проверку и сохраняет результат."""
        print(f"\n🔍 Running: {name}...")
        try:
            result = check_func(**kwargs)
            self.results["checks"].append({
                "name": name,
                "status": "passed" if result["success"] else "failed",
                "issues": result.get("issues", []),
                "warnings": result.get("warnings", []),
                "duration": result.get("duration", 0)
            })
            
            self.results["summary"]["total"] += 1
            if result["success"]:
                self.results["summary"]["passed"] += 1
                print(f"✅ {name}: PASSED")
            else:
                self.results["summary"]["failed"] += 1
                print(f"❌ {name}: FAILED ({len(result.get('issues', []))} issues)")
                
            if result.get("warnings"):
                self.results["summary"]["warnings"] += len(result["warnings"])
                print(f"⚠️  {name}: {len(result['warnings'])} warnings")
                
        except Exception as e:
            self.results["checks"].append({
                "name": name,
                "status": "error",
                "error": str(e)
            })
            self.results["summary"]["total"] += 1
            self.results["summary"]["failed"] += 1
            print(f"❌ {name}: ERROR - {e}")
    
    def run_all(self):
        """Запускает все проверки."""
        print("🚀 Starting AFL Orchestrator Documentation Validation")
        print("=" * 60)
        
        # 1. Проверка ссылок
        self.run_check(
            "Markdown Links",
            check_markdown_links,
            docs_dir=self.docs_dir
        )
        
        # 2. Проверка терминологии
        self.run_check(
            "Terminology Consistency",
            check_terminology_consistency,
            docs_dir=self.docs_dir
        )
        
        # 3. Кросс-документ консистентность
        self.run_check(
            "Cross-Document Consistency",
            check_cross_document_consistency,
            docs_dir=self.docs_dir
        )
        
        # 4. Проверка таблиц
        self.run_check(
            "Markdown Tables",
            check_markdown_tables,
            docs_dir=self.docs_dir
        )
        
        # 5. Проверка SQL синтаксиса
        self.run_check(
            "SQL Syntax",
            check_sql_syntax,
            docs_dir=self.docs_dir
        )
        
        print("\n" + "=" * 60)
        print("📊 Validation Summary:")
        print(f"   Total checks: {self.results['summary']['total']}")
        print(f"   ✅ Passed: {self.results['summary']['passed']}")
        print(f"   ❌ Failed: {self.results['summary']['failed']}")
        print(f"   ⚠️  Warnings: {self.results['summary']['warnings']}")
        
        return self.results["summary"]["failed"] == 0
    
    def save_results(self):
        """Сохраняет результаты в JSON и генерирует HTML отчёт."""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # JSON отчёт
        json_path = self.output_dir / "validation_results.json"
        import json
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)
        print(f"\n💾 Results saved to: {json_path}")
        
        # HTML отчёт
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
        from scripts.reports.generate_report import generate_html_report
        html_path = generate_html_report(self.results, self.output_dir)
        print(f"📄 HTML Report saved to: {html_path}")


def main():
    parser = argparse.ArgumentParser(
        description="AFL Orchestrator Documentation Pre-Validation"
    )
    parser.add_argument(
        "--docs-dir",
        default=DEFAULT_DOCS_DIR,
        help=f"Directory with documentation files (default: {DEFAULT_DOCS_DIR})"
    )
    parser.add_argument(
        "--output-dir",
        default=DEFAULT_OUTPUT_DIR,
        help=f"Directory for output reports (default: {DEFAULT_OUTPUT_DIR})"
    )
    parser.add_argument(
        "--fail-on-warning",
        action="store_true",
        help="Exit with error code if there are warnings"
    )
    
    args = parser.parse_args()
    
    # Валидация путей
    if not Path(args.docs_dir).exists():
        print(f"❌ Error: Documentation directory not found: {args.docs_dir}")
        sys.exit(1)
    
    # Запуск валидации
    runner = ValidationRunner(args.docs_dir, args.output_dir)
    success = runner.run_all()
    runner.save_results()
    
    # Exit code для CI/CD
    if not success:
        print("\n❌ Validation FAILED")
        sys.exit(1)
    elif args.fail_on_warning and runner.results["summary"]["warnings"] > 0:
        print("\n⚠️  Validation passed with warnings")
        sys.exit(1)
    else:
        print("\n✅ Validation PASSED")
        sys.exit(0)


if __name__ == "__main__":
    main()