import sqlite3
from pathlib import Path

db_path = Path("callcenter.db")
if not db_path.exists():
    db_path = Path("backend/callcenter.db")

conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# ตรวจสอบข้อมูลเคส #113 ที่เห็นในหน้าต่าง
cursor.execute("SELECT * FROM call_records WHERE id = 113;")
row = cursor.fetchone()

if row:
    print("=== ข้อมูลเคส #113 ในฐานข้อมูล ===")
    for k in row.keys():
        if row[k] is not None:
            print(f"{k}: {row[k]}")
else:
    print("ไม่พบเคส #113")

conn.close()
