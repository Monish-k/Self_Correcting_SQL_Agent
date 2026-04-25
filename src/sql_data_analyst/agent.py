from __future__ import annotations

import json
from typing import Any, Dict, List, Tuple

import pandas as pd

from .config import AppConfig
from .data_loading import load_uploaded_structured_file
from .db_tools import build_schema_context, run_sql
from .modeling import SQLModel
from .prompts import SYSTEM_PROMPT, REPAIR_SYSTEM_PROMPT
from .safety import extract_sql, is_safe_sql, maybe_retry_on_empty


class SQLAgent:
    def __init__(self, config: AppConfig):
        self.config = config
        self.model = SQLModel(config)

    def draft_sql(self, question: str, schema_context: str) -> Tuple[str, str]:
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"Schema context:\n{schema_context}\n\n"
                    f"Question:\n{question}\n\n"
                    f"Return only executable SQLite SQL."
                ),
            },
        ]
        raw = self.model.generate_completion(messages, max_new_tokens=self.config.sql_max_new_tokens)
        return raw, extract_sql(raw)

    def repair_sql(self, question: str, schema_context: str, failed_sql: str, error_message: str) -> Tuple[str, str]:
        messages = [
            {"role": "system", "content": REPAIR_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"Schema context:\n{schema_context}\n\n"
                    f"Question:\n{question}\n\n"
                    f"Failed SQL:\n{failed_sql}\n\n"
                    f"SQLite error:\n{error_message}\n\n"
                    f"Return only corrected executable SQLite SQL."
                ),
            },
        ]
        raw = self.model.generate_completion(messages, max_new_tokens=self.config.repair_max_new_tokens)
        return raw, extract_sql(raw)

    def summarize_result(self, result_obj: Dict[str, Any]) -> str:
        columns = result_obj.get("columns", [])
        rows = result_obj.get("rows", [])
        row_count = len(rows)

        if row_count == 0:
            return "The query ran successfully but returned no rows."

        preview = rows[:3]
        return (
            f"The query returned {row_count} row(s). "
            f"Columns: {', '.join(columns)}. "
            f"First rows: {preview}"
        )

    def ask(self, question: str, file_path: str | None):
        db_path = load_uploaded_structured_file(file_path)
        schema_context = build_schema_context(db_path, self.config)
        trace: List[Dict[str, Any]] = []

        raw_draft, sql = self.draft_sql(question, schema_context)
        trace.append({"step": "draft_sql", "raw": raw_draft, "sql": sql})

        if not is_safe_sql(sql):
            trace.append({"step": "safety_block", "reason": "Only SELECT/WITH read-only SQL is allowed."})
            raw_fix, fixed_sql = self.repair_sql(question, schema_context, sql, "Only SELECT or WITH queries are allowed.")
            trace.append({"step": "repair_after_safety", "raw": raw_fix, "sql": fixed_sql})
            sql = fixed_sql

        ok, out = run_sql(db_path, sql) if is_safe_sql(sql) else (False, "Unsafe SQL after repair.")

        if ok:
            if len(out["rows"]) == 0 and maybe_retry_on_empty(question):
                trace.append({"step": "empty_result_after_draft", "rows": 0})
            else:
                summary = self.summarize_result(out)
                df = pd.DataFrame(out["rows"][: self.config.max_result_rows_display], columns=out["columns"]) if out["columns"] else pd.DataFrame()
                return schema_context, sql, df, summary, json.dumps(trace, indent=2, ensure_ascii=False)
        else:
            trace.append({"step": "execution_error", "error": out})

        current_sql = sql
        current_error = out if not ok else "Query executed but returned empty results."

        for retry_idx in range(self.config.max_retries):
            raw_fix, fixed_sql = self.repair_sql(question, schema_context, current_sql, str(current_error))
            trace.append({"step": f"repair_{retry_idx+1}", "raw": raw_fix, "sql": fixed_sql})

            if not is_safe_sql(fixed_sql):
                trace.append({"step": f"repair_{retry_idx+1}_unsafe", "reason": "Unsafe SQL blocked."})
                current_sql = fixed_sql
                current_error = "Only read-only SELECT or WITH queries are allowed."
                continue

            ok2, out2 = run_sql(db_path, fixed_sql)
            if ok2:
                if len(out2["rows"]) == 0 and maybe_retry_on_empty(question) and retry_idx < (self.config.max_retries - 1):
                    trace.append({"step": f"repair_{retry_idx+1}_empty_result", "rows": 0})
                    current_sql = fixed_sql
                    current_error = "Query executed but returned empty results."
                    continue

                summary = self.summarize_result(out2)
                df = pd.DataFrame(out2["rows"][: self.config.max_result_rows_display], columns=out2["columns"]) if out2["columns"] else pd.DataFrame()
                return schema_context, fixed_sql, df, summary, json.dumps(trace, indent=2, ensure_ascii=False)

            trace.append({"step": f"repair_{retry_idx+1}_error", "error": out2})
            current_sql = fixed_sql
            current_error = out2

        return schema_context, current_sql, pd.DataFrame(), "The agent could not produce a valid SQL answer after retries.", json.dumps(trace, indent=2, ensure_ascii=False)
