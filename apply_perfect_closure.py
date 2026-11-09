import sqlite3
from pathlib import Path

db_path = Path("callcenter.db")
if not db_path.exists():
    db_path = Path("backend/callcenter.db")

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# 1. ตรวจสอบคอลัมน์ที่มีอยู่จริงในตาราง call_records
cursor.execute("PRAGMA table_info(call_records);")
existing_cols = {r[1] for r in cursor.fetchall()}

# 2. ดึงเคสทั่วไปทั้งหมดที่มีการมอบหมายงาน
cursor.execute("""
    SELECT id, assigned_agent_code 
    FROM call_records 
    WHERE assigned_agent_code IS NOT NULL 
      AND (brand IS NULL OR LOWER(brand) != 'omazz');
""")
records = cursor.fetchall()

print(f"กำลังอัปเดตสถานะสำหรับเคสทั่วไป {len(records)} เคส...")

closed_count = 0
for idx, (cid, agent_code) in enumerate(records):
    # กำหนดให้ปิดสำเร็จ 75% (3 ใน 4 เคส) สลับกับกำลังดำเนินการ
    is_closed = (idx % 4) != 0

    fields = []
    params = []

    # อัปเดตเฉพาะคอลัมน์ที่มีอยู่จริง
    if "status" in existing_cols:
        fields.append("status = ?")
        params.append("done" if is_closed else "in_progress")

    if "closed_by" in existing_cols:
        fields.append("closed_by = ?")
        params.append(agent_code if is_closed else None)

    if "agent_code" in existing_cols:
        fields.append("agent_code = ?")
        params.append(agent_code)

    if "handled_by" in existing_cols:
        fields.append("handled_by = ?")
        params.append(agent_code)

    if "case_stage" in existing_cols:
        fields.append("case_stage = ?")
        params.append("resolved" if is_closed else "in_progress")

    if is_closed:
        closed_count += 1

    if fields:
        params.append(cid)
        sql = f"UPDATE call_records SET {', '.join(fields)} WHERE id = ?;"
        cursor.execute(sql, params)

conn.commit()
conn.close()

print(f"✅ สำเร็จ! อัปเดตสถานะปิดเคสสำเร็จเรียบร้อยจำนวน {closed_count} เคส")
