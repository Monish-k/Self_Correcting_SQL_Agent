from __future__ import annotations

import re


def strip_code_fences(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^```sql\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"^```\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


def extract_sql(text: str) -> str:
    text = strip_code_fences(text)
    patterns = [
        r"(?is)(with\s.+?;)",
        r"(?is)(select\s.+?;)",
        r"(?is)(with\s.+)",
        r"(?is)(select\s.+)",
    ]
    for pattern in patterns:
        m = re.search(pattern, text)
        if m:
            return m.group(1).strip()
    return text.strip()


def is_safe_sql(sql: str) -> bool:
    sql_norm = sql.strip().lower().lstrip()
    if not (sql_norm.startswith("select") or sql_norm.startswith("with")):
        return False

    banned = [" insert ", " update ", " delete ", " drop ", " alter ", " create ", " attach ", " pragma "]
    check = f" {sql_norm} "
    return not any(tok in check for tok in banned)


def maybe_retry_on_empty(question: str) -> bool:
    q = question.lower()
    keywords = ["top", "highest", "lowest", "how many", "count", "total", "sum", "average", "avg"]
    return any(k in q for k in keywords)
