from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(slots=True)
class AppConfig:
    base_model_id: str = os.getenv("SQL_AGENT_BASE_MODEL", "Qwen/Qwen3-4B-Instruct-2507")
    adapter_source: str = os.getenv("SQL_AGENT_ADAPTER", "")
    hf_token: str | None = os.getenv("HF_TOKEN")
    host: str = os.getenv("SQL_AGENT_HOST", "0.0.0.0")
    port: int = int(os.getenv("SQL_AGENT_PORT", "7860"))

    # Latency controls
    schema_preview_rows: int = int(os.getenv("SQL_AGENT_SCHEMA_PREVIEW_ROWS", "1"))
    schema_max_tables: int = int(os.getenv("SQL_AGENT_SCHEMA_MAX_TABLES", "6"))
    schema_max_columns: int = int(os.getenv("SQL_AGENT_SCHEMA_MAX_COLUMNS", "12"))
    schema_max_chars: int = int(os.getenv("SQL_AGENT_SCHEMA_MAX_CHARS", "3500"))
    schema_max_join_hints: int = int(os.getenv("SQL_AGENT_SCHEMA_MAX_JOIN_HINTS", "6"))
    max_input_tokens: int = int(os.getenv("SQL_AGENT_MAX_INPUT_TOKENS", "640"))
    sql_max_new_tokens: int = int(os.getenv("SQL_AGENT_SQL_MAX_NEW_TOKENS", "96"))
    repair_max_new_tokens: int = int(os.getenv("SQL_AGENT_REPAIR_MAX_NEW_TOKENS", "96"))
    max_retries: int = int(os.getenv("SQL_AGENT_MAX_RETRIES", "1"))
    max_result_rows_display: int = int(os.getenv("SQL_AGENT_MAX_RESULT_ROWS_DISPLAY", "100"))

    def validate(self) -> None:
        if not self.adapter_source:
            raise ValueError(
                "SQL_AGENT_ADAPTER is not set. Point it to a local adapter path or a Hugging Face model repo."
            )
