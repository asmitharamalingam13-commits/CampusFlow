import sqlite3

db_path = "instance/campusflow.db"

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

columns = [
    ("event_id", "INTEGER"),
    ("student_id", "INTEGER"),
    ("status", "VARCHAR(20) DEFAULT 'PENDING'"),
    ("marked_at", "DATETIME"),
]

existing_columns = {
    row[1]
    for row in cursor.execute(
        "PRAGMA table_info(od_period_snapshots)"
    ).fetchall()
}

for column_name, column_type in columns:

    if column_name not in existing_columns:

        cursor.execute(
            f"ALTER TABLE od_period_snapshots "
            f"ADD COLUMN {column_name} {column_type}"
        )

        print(f"Added column: {column_name}")

    else:

        print(f"Already exists: {column_name}")

conn.commit()
conn.close()

print("OD snapshot table fixed successfully.")