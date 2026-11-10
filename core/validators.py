"""Structure + safety validation for generated bot projects."""
from __future__ import annotations

import ast
import re
from typing import Dict, List, Tuple

from core.schemas import REQUIRED_FILES

# Patterns that must never appear in generated code
DANGEROUS_PATTERNS: List[Tuple[str, str]] = [
    (r"\beval\s*\(", "eval() is forbidden"),
    (r"\bexec\s*\(", "exec() is forbidden"),
    (r"\bcompile\s*\(", "compile() is forbidden"),
    (r"os\.system\s*\(", "os.system() is forbidden"),
    (r"subprocess\.[a-zA-Z_]+ \(.*shell\s*=\s*True", "subprocess shell=True is forbidden"),
    (r"__import__\s*\(", "dynamic __import__ is forbidden"),
    (r"BOT_TOKEN\s*=\s*['\"][0-9]{6,}:[A-Za-z0-9_-]+", "Hardcoded BOT_TOKEN detected"),
    (r"api_key\s*=\s*['\"]sk-[A-Za-z0-9]+", "Hardcoded API key detected"),
    (r"pickle\.loads?\s*\(", "pickle load is forbidden"),
]


def check_required_files(files: Dict[str, str]) -> List[str]:
    missing = [f for f in REQUIRED_FILES if f not in files]
    return [f"Missing required file: {m}" for m in missing]


def check_dangerous_patterns(files: Dict[str, str]) -> List[str]:
    issues: List[str] = []
    for path, content in files.items():
        if not path.endswith((".py", ".sh", ".env", ".txt", ".md")):
            continue
        for pattern, msg in DANGEROUS_PATTERNS:
            if re.search(pattern, content, re.IGNORECASE | re.DOTALL):
                issues.append(f"{path}: {msg}")
    return issues


def check_python_syntax(files: Dict[str, str]) -> List[str]:
    """AST-parse every .py file; report syntax errors."""
    errors: List[str] = []
    for path, content in files.items():
        if not path.endswith(".py"):
            continue
        try:
            ast.parse(content, filename=path)
        except SyntaxError as e:
            errors.append(f"{path}: syntax error line {e.lineno}: {e.msg}")
    return errors


def check_aiogram_basics(files: Dict[str, str]) -> List[str]:
    """Lightweight semantic checks for aiogram projects."""
    issues: List[str] = []
    main = files.get("main.py", "")
    all_py = "\n".join(v for k, v in files.items() if k.endswith(".py"))

    if "aiogram" not in all_py and "aiogram" not in files.get("requirements.txt", ""):
        issues.append("aiogram not found in code or requirements")

    if main:
        if "Bot(" not in main and "Bot (" not in main:
            issues.append("main.py: Bot() instantiation not found")
        if "start_polling" not in main and "set_webhook" not in main and "run_polling" not in main:
            # still ok if they use dp.run_polling differently
            if "Dispatcher" not in main and "Dispatcher" not in all_py:
                issues.append("main.py: Dispatcher / polling entry not found")

    # Token must come from env somewhere
    if re.search(r"BOT_TOKEN\s*=\s*['\"][0-9]", all_py):
        issues.append("Possible hardcoded BOT_TOKEN")
    elif "BOT_TOKEN" not in all_py and "bot_token" not in all_py.lower():
        # config might load differently
        if "getenv" not in all_py and "BaseSettings" not in all_py and "dotenv" not in all_py:
            issues.append("No env-based token loading pattern detected")

    return issues


def validate_package(files: Dict[str, str]) -> Tuple[bool, List[str]]:
    """
    Full validation pipeline.
    Returns (is_ok, list_of_issues).
    Critical issues (dangerous + missing required + syntax) → is_ok False.
    """
    issues: List[str] = []
    issues.extend(check_required_files(files))
    issues.extend(check_dangerous_patterns(files))
    issues.extend(check_python_syntax(files))
    soft = check_aiogram_basics(files)

    critical_prefixes = ("Missing required", "syntax error", "forbidden", "Hardcoded", "pickle")
    critical = [i for i in issues if any(p in i for p in critical_prefixes)]
    # dangerous patterns already in issues
    is_ok = len(critical) == 0 and not any("forbidden" in i or "Hardcoded" in i for i in issues)

    # attach soft warnings too
    all_issues = issues + [f"[warn] {s}" for s in soft]
    return is_ok, all_issues
