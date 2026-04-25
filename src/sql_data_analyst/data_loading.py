from __future__ import annotations

import os
import re
import shutil
import sqlite3
from pathlib import Path
from typing import Optional

import pandas as pd

WORKDIR = Path("/tmp/sql_agent_space")
WORKDIR.mkdir(parents=True, exist_ok=True)
DEFAULT_DB_PATH = WORKDIR / "default_demo.db"


def create_default_demo_db(db_path: Path = DEFAULT_DB_PATH) -> None:
    if db_path.exists():
        return

    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()
    cur.executescript(
        """
        CREATE TABLE customers (
            customer_id INTEGER PRIMARY KEY,
            customer_name TEXT,
            city TEXT,
            plan_type TEXT
        );
        CREATE TABLE products (
            product_id INTEGER PRIMARY KEY,
            product_name TEXT,
            category TEXT,
            unit_price REAL
        );
        CREATE TABLE orders (
            order_id INTEGER PRIMARY KEY,
            customer_id INTEGER,
            order_date TEXT,
            status TEXT,
            FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
        );
        CREATE TABLE order_items (
            order_item_id INTEGER PRIMARY KEY,
            order_id INTEGER,
            product_id INTEGER,
            quantity INTEGER,
            discount REAL,
            FOREIGN KEY (order_id) REFERENCES orders(order_id),
            FOREIGN KEY (product_id) REFERENCES products(product_id)
        );
        """
    )

    customers = [
        (1, "Alice", "Chennai", "Free"),
        (2, "Bob", "Bengaluru", "Paid"),
        (3, "Carla", "Mumbai", "Paid"),
        (4, "Dinesh", "Chennai", "Free"),
    ]
    products = [
        (1, "Notebook", "Stationery", 100.0),
        (2, "Pen", "Stationery", 20.0),
        (3, "Desk Lamp", "Electronics", 800.0),
        (4, "Mouse", "Electronics", 600.0),
    ]
    orders = [
        (1, 1, "2025-01-10", "completed"),
        (2, 2, "2025-01-12", "completed"),
        (3, 3, "2025-02-05", "completed"),
        (4, 2, "2025-02-15", "returned"),
        (5, 4, "2025-03-01", "completed"),
    ]
    order_items = [
        (1, 1, 1, 2, 0.0),
        (2, 1, 2, 3, 0.0),
        (3, 2, 3, 1, 50.0),
        (4, 2, 4, 1, 0.0),
        (5, 3, 1, 5, 20.0),
        (6, 4, 4, 1, 0.0),
        (7, 5, 2, 10, 10.0),
    ]

    cur.executemany("INSERT INTO customers VALUES (?, ?, ?, ?)", customers)
    cur.executemany("INSERT INTO products VALUES (?, ?, ?, ?)", products)
    cur.executemany("INSERT INTO orders VALUES (?, ?, ?, ?)", orders)
    cur.executemany("INSERT INTO order_items VALUES (?, ?, ?, ?, ?)", order_items)

    conn.commit()
    conn.close()


def sanitize_table_name(name: str) -> str:
    name = re.sub(r"[^a-zA-Z0-9_]", "_", name)
    if not name:
        name = "table1"
    if name[0].isdigit():
        name = f"t_{name}"
    return name.lower()


def csv_to_sqlite(csv_path: str, sqlite_path: str, table_name: Optional[str] = None) -> str:
    if os.path.exists(sqlite_path):
        os.remove(sqlite_path)

    df = pd.read_csv(csv_path)
    table_name = table_name or sanitize_table_name(Path(csv_path).stem)

    conn = sqlite3.connect(sqlite_path)
    df.to_sql(table_name, conn, index=False, if_exists="replace")
    conn.close()
    return sqlite_path


def excel_to_sqlite(xlsx_path: str, sqlite_path: str) -> str:
    if os.path.exists(sqlite_path):
        os.remove(sqlite_path)

    xls = pd.ExcelFile(xlsx_path)
    conn = sqlite3.connect(sqlite_path)

    for sheet in xls.sheet_names:
        df = pd.read_excel(xlsx_path, sheet_name=sheet)
        table_name = sanitize_table_name(sheet)
        df.to_sql(table_name, conn, index=False, if_exists="replace")

    conn.close()
    return sqlite_path


def load_uploaded_structured_file(file_path: Optional[str]) -> str:
    if file_path is None:
        create_default_demo_db(DEFAULT_DB_PATH)
        return str(DEFAULT_DB_PATH)

    suffix = Path(file_path).suffix.lower()
    out_path = str(WORKDIR / "uploaded_user_data.db")

    if suffix in [".sqlite", ".db"]:
        shutil.copy(file_path, out_path)
        return out_path
    if suffix == ".csv":
        return csv_to_sqlite(file_path, out_path)
    if suffix in [".xlsx", ".xls"]:
        return excel_to_sqlite(file_path, out_path)

    raise ValueError(f"Unsupported file type: {suffix}. Upload .db, .sqlite, .csv, .xlsx, or .xls")
