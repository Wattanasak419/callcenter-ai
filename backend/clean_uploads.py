import os
import sqlite3

# ระบุ Path ไฟล์ .db ให้ตรงกับที่โปรเจกต์ใช้งานจริง
DB_PATH = "backend/database.db"

if not os.path.exists(DB_PATH):
  print(f"❌ ไม่พบไฟล์ฐานข้อมูลที่: {DB_PATH}")
  exit()

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# ดึงรายชื่อตารางทั้งหมดในฐานข้อมูล
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = [row[0] for row in cursor.fetchall()]
print("📋 ตารางทั้งหมดที่มีในระบบ:", tables)

# แสดงโครงสร้างคอลัมน์ของแต่ละตาราง
for t in tables:
  cursor.execute(f"PRAGMA table_info({t});")
  cols = [c[1] for c in cursor.fetchall()]
  print(f" - ตาราง '{t}' มีคอลัมน์: {cols}")

conn.close()