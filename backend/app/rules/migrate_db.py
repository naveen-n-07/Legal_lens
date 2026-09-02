"""
migrate_db.py - Safe database column migration for ComplianceRuleDB SQLite table
"""

import sqlite3
import os

def migrate_database_schema():
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    db_paths = [
        os.path.join(base_dir, "backend", "metrix_lm.db"),
        os.path.join(base_dir, "metrix_lm.db")
    ]

    needed_cols = [
        ("regulation", "VARCHAR"),
        ("regulation_section", "VARCHAR"),
        ("product_category", "VARCHAR DEFAULT 'ALL'"),
        ("field_name", "VARCHAR"),
        ("rule_type", "VARCHAR DEFAULT 'MANDATORY_FIELD'"),
        ("condition", "TEXT"),
        ("required", "BOOLEAN DEFAULT 1"),
        ("severity", "VARCHAR DEFAULT 'HIGH'"),
        ("error_message", "TEXT"),
        ("explanation", "TEXT"),
        ("effective_from", "DATETIME"),
        ("effective_to", "DATETIME"),
        ("version", "VARCHAR DEFAULT '1.0.0'"),
        ("source_reference", "VARCHAR"),
        ("is_active", "BOOLEAN DEFAULT 1"),
        ("created_at", "DATETIME"),
        ("updated_at", "DATETIME")
    ]

    for db_path in db_paths:
        if not os.path.exists(db_path):
            continue
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute("PRAGMA table_info(compliance_rules);")
        existing_cols = {col[1] for col in cur.fetchall()}

        for col_name, col_type in needed_cols:
            if col_name not in existing_cols:
                try:
                    cur.execute(f"ALTER TABLE compliance_rules ADD COLUMN {col_name} {col_type};")
                    print(f"Added column {col_name} to {db_path}")
                except Exception as e:
                    print(f"Notice adding {col_name}: {e}")

        conn.commit()
        conn.close()

if __name__ == "__main__":
    migrate_database_schema()
