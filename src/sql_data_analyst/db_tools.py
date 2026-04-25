from __future__ import annotations

import sqlite3
from typing import Any, Dict, List, Tuple

from .config import AppConfig


def list_tables(db_path: str) -> List[str]:
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type='table' AND name NOT LIKE 'sqlite_%'
        ORDER BY name
        """
    )
    tables = [row[0] for row in cur.fetchall()]
    conn.close()
    return tables


def get_table_columns(db_path: str, table_name: str) -> List[Dict[str, Any]]:
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute(f"PRAGMA table_info('{table_name}')")
    rows = cur.fetchall()
    conn.close()

    return [
        {
            "cid": r[0],
            "name": r[1],
            "type": r[2],
            "notnull": r[3],
            "default_value": r[4],
            "pk": r[5],
        }
        for r in rows
    ]


def preview_rows(db_path: str, table_name: str, limit: int) -> List[Tuple[Any, ...]]:
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute(f"SELECT * FROM '{table_name}' LIMIT {limit}")
    rows = cur.fetchall()
    conn.close()
    return rows


def infer_join_hints(db_path: str) -> List[str]:
    tables = list_tables(db_path)
    table_cols = {t: [c["name"] for c in get_table_columns(db_path, t)] for t in tables}
    hints = []

    for i, t1 in enumerate(tables):
        for t2 in tables[i + 1 :]:
            common = set(table_cols[t1]).intersection(set(table_cols[t2]))
            common = [c for c in common if c.endswith("_id") or c == "id"]
            if common:
                hints.append(f"{t1} ↔ {t2} on {sorted(common)}")

    return hints


def build_schema_context(db_path: str, config: AppConfig) -> str:
    tables = list_tables(db_path)[: config.schema_max_tables]
    parts = []

    for table in tables:
        cols = get_table_columns(db_path, table)[: config.schema_max_columns]
        rows = preview_rows(db_path, table, limit=config.schema_preview_rows)

        parts.append(f"TABLE: {table}")
        parts.append("COLUMNS: " + ", ".join([f"{c['name']} ({c['type']})" for c in cols]))

        if rows:
            parts.append(f"SAMPLE: {rows[:config.schema_preview_rows]}")
        parts.append("")

    join_hints = infer_join_hints(db_path)[: config.schema_max_join_hints]
    if join_hints:
        parts.append("JOIN HINTS:")
        parts.extend(join_hints)

    schema_text = "\n".join(parts).strip()
    if len(schema_text) > config.schema_max_chars:
        schema_text = schema_text[: config.schema_max_chars] + "\n...[truncated schema context]"
    return schema_text


def run_sql(db_path: str, sql: str):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    try:
        cur.execute(sql)
        columns = [d[0] for d in cur.description] if cur.description else []
        rows = cur.fetchall()
        conn.close()
        return True, {"columns": columns, "rows": rows}
    except Exception as e:
        conn.close()
        return False, str(e)
