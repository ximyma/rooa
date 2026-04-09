import sqlite3, os, sys

# 强制 UTF-8 输出
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

DB_PATH = os.path.join(os.path.dirname(__file__), 'instance', 'ooa.db')
if not os.path.exists(DB_PATH):
    for root, dirs, files in os.walk(os.path.dirname(__file__)):
        for f in files:
            if f.endswith('.db'):
                DB_PATH = os.path.join(root, f)
                break

print("DB:", DB_PATH)
conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

cur.execute("PRAGMA table_info(users)")
existing = {row[1] for row in cur.fetchall()}
print("Existing columns:", sorted(existing))

new_cols = [
    ("org_id", "INTEGER"),
    ("dept_id", "INTEGER"),
    ("position_id", "INTEGER"),
    ("employee_no", "VARCHAR(30)"),
    ("avatar", "VARCHAR(200)"),
    ("gender", "VARCHAR(5) DEFAULT 'unknown'"),
    ("is_active", "BOOLEAN DEFAULT 1"),
    ("remark", "VARCHAR(300)"),
]

for col_name, col_type in new_cols:
    if col_name not in existing:
        try:
            cur.execute(f"ALTER TABLE users ADD COLUMN {col_name} {col_type}")
            print(f"  ADDED: users.{col_name}")
        except Exception as e:
            print(f"  SKIP: users.{col_name} - {e}")
    else:
        print(f"  EXISTS: users.{col_name}")

conn.commit()
conn.close()
print("DONE - fields migration complete")
