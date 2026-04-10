#!/usr/bin/env python3
"""
Генерация HTML отчёта о валидации.
"""

from pathlib import Path
from datetime import datetime
from typing import Dict

def generate_html_report(results: Dict, output_dir: Path) -> Path:
    """Генерирует HTML отчёт из результатов валидации."""
    
    html_template = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AFL Orchestrator — Documentation Validation Report</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 40px; background: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 40px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        h1 {{ color: #333; border-bottom: 2px solid #007bff; padding-bottom: 10px; }}
        .summary {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px; margin: 30px 0; }}
        .card {{ padding: 20px; border-radius: 8px; text-align: center; }}
        .card.total {{ background: #e3f2fd; }}
        .card.passed {{ background: #e8f5e9; }}
        .card.failed {{ background: #ffebee; }}
        .card.warnings {{ background: #fff3e0; }}
        .card h3 {{ margin: 0; font-size: 14px; color: #666; }}
        .card .number {{ font-size: 36px; font-weight: bold; margin: 10px 0; }}
        .check {{ margin: 20px 0; padding: 20px; border: 1px solid #ddd; border-radius: 8px; }}
        .check.passed {{ border-left: 4px solid #4caf50; }}
        .check.failed {{ border-left: 4px solid #f44336; }}
        .issue {{ background: #ffebee; padding: 10px; margin: 10px 0; border-radius: 4px; }}
        .issue code {{ background: #f5f5f5; padding: 2px 6px; border-radius: 3px; font-family: monospace; }}
        .timestamp {{ color: #999; font-size: 12px; }}
        table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
        th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }}
        th {{ background: #f5f5f5; }}
        .status {{ padding: 4px 8px; border-radius: 4px; font-size: 12px; font-weight: bold; }}
        .status.passed {{ background: #4caf50; color: white; }}
        .status.failed {{ background: #f44336; color: white; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>📋 AFL Orchestrator Documentation Validation Report</h1>
        <p class="timestamp">Generated: {timestamp}</p>
        
        <div class="summary">
            <div class="card total">
                <h3>Total Checks</h3>
                <div class="number">{total}</div>
            </div>
            <div class="card passed">
                <h3>✅ Passed</h3>
                <div class="number">{passed}</div>
            </div>
            <div class="card failed">
                <h3>❌ Failed</h3>
                <div class="number">{failed}</div>
            </div>
            <div class="card warnings">
                <h3>⚠️ Warnings</h3>
                <div class="number">{warnings}</div>
            </div>
        </div>
        
        <h2>Check Details</h2>
        {checks_html}
        
        <h2>Issues Summary</h2>
        {issues_table}
    </div>
</body>
</html>
"""
    
    # Генерация HTML для каждой проверки
    checks_html = ""
    all_issues = []
    
    for check in results["checks"]:
        status_class = "passed" if check["status"] == "passed" else "failed"
        status_text = "✅ PASSED" if check["status"] == "passed" else "❌ FAILED"
        
        issues_html = ""
        if check.get("issues"):
            for issue in check["issues"]:
                issues_html += f"""
                <div class="issue">
                    <strong>{issue.get('type', 'Issue')}</strong>: {issue.get('message', '')}<br>
                    <code><strong>Context</strong>: {issue.get('context', '')}</code><br>
                    <code><strong>Recommended</strong>: {issue.get('recommended', '')}</code><br>
                    <code>{issue.get('file', '')}:{issue.get('line', issue.get('block', 'N/A'))}</code>
                </div>
                """
                all_issues.append(issue)
        
        checks_html += f"""
        <div class="check {status_class}">
            <h3>{check['name']} <span class="status {status_class}">{status_text}</span></h3>
            <p>Duration: {check.get('duration', 0)}s</p>
            {issues_html}
        </div>
        """
    
    # Таблица всех_issues
    issues_table = """
    <table>
        <thead>
            <tr>
                <th>File</th>
                <th>Line</th>
                <th>Type</th>
                <th>Message</th>
            </tr>
        </thead>
        <tbody>
    """
    
    for issue in all_issues:
        issues_table += f"""
            <tr>
                <td><code>{issue.get('file', 'N/A')}</code></td>
                <td>{issue.get('line', issue.get('block', 'N/A'))}</td>
                <td>{issue.get('type', 'N/A')}</td>
                <td>{issue.get('message', 'N/A')}</td>
            </tr>
        """
    
    issues_table += "</tbody></table>"
    
    # Заполнение шаблона
    html_content = html_template.format(
        timestamp=results["timestamp"],
        total=results["summary"]["total"],
        passed=results["summary"]["passed"],
        failed=results["summary"]["failed"],
        warnings=results["summary"]["warnings"],
        checks_html=checks_html,
        issues_table=issues_table if all_issues else "<p>🎉 No issues found!</p>"
    )
    
    # Сохранение
    html_path = output_dir / "validation_report.html"
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    
    return html_path