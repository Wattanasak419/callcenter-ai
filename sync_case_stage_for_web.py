import sqlite3
from pathlib import Path

db_path = Path("callcenter.db")
if not db_path.exists():
    db_path = Path("backend/callcenter.db")

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# ตรวจสอบคอลัมน์ case_stage
cursor.execute("PRAGMA table_info(call_records);")
cols = [r[1] for r in cursor.fetchall()]

if "case_stage" not in cols:
    cursor.execute("ALTER TABLE call_records ADD COLUMN case_stage TEXT DEFAULT 'in_progress';")
    print("เพิ่มคอลัมน์ case_stage เรียบร้อย")

# ปรับค่าเคสที่สถานะเป็น done ให้มี case_stage = 'resolved' เพื่อให้ main.py บรรทัด 1649 จับคู่ได้
cursor.execute("UPDATE call_records SET case_stage = 'resolved' WHERE status = 'done' OR closed_by IS NOT NULL;")
cursor.execute("UPDATE call_records SET case_stage = 'in_progress' WHERE status != 'done' AND closed_by IS NULL;")

conn.commit()
conn.close()
print("✅ ซิงค์ case_stage ให้ระบบหลังบ้านของหน้าเว็บเรียบร้อยแล้ว!")
