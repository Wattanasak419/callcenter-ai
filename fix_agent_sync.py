import sqlite3
from pathlib import Path

db_path = Path("callcenter.db")
if not db_path.exists():
    db_path = Path("backend/callcenter.db")

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# 1. ตรวจสอบคอลัมน์ทั้งหมด
cursor.execute("PRAGMA table_info(call_records);")
cols = [r[1] for r in cursor.fetchall()]

# 2. ดึงเคสทั่วไปทั้งหมด
cursor.execute("SELECT id, assigned_agent_code FROM call_records WHERE brand IS NULL OR LOWER(brand) != 'omazz';")
cases = cursor.fetchall()

print(f"กำลังซิงค์ข้อมูลพนักงานและสถานะปิดเคส {len(cases)} เคส...")

for idx, (cid, assigned_code) in enumerate(cases):
    # กำหนดให้ปิดเคสสำเร็จประมาณ 70-80% (สลับให้มีทั้งปิดแล้วและกำลังดำเนินการ)
    is_closed = (idx % 4) != 0  # 3 ใน 4 เคส (75%) ปิดสำเร็จ
    
    status_thai = "ปิดเคสสำเร็จ" if is_closed else "กำลังดำเนินการ"
    status_eng = "closed" if is_closed else "in_progress"
    
    fields = []
    params = []
    
    # ซิงค์รหัสพนักงานให้ตรงกันทุกคอลัมน์
    if assigned_code:
        if "agent_code" in cols:
            fields.append("agent_code = ?")
            params.append(assigned_code)
        if "closed_by" in cols:
            fields.append("closed_by = ?")
            params.append(assigned_code if is_closed else None)
        if "handled_by" in cols:
            fields.append("handled_by = ?")
            params.append(assigned_code)

    # อัปเดตสถานะ
    if "status" in cols:
        fields.append("status = ?")
        params.append(status_thai)
        
    if "case_stage" in cols:
        fields.append("case_stage = ?")
        params.append(status_eng)
        
    if "is_resolved" in cols:
        fields.append("is_resolved = ?")
        params.append(1 if is_closed else 0)
        
    if "is_closed" in cols:
        fields.append("is_closed = ?")
        params.append(1 if is_closed else 0)

    params.append(cid)
    sql = f"UPDATE call_records SET {', '.join(fields)} WHERE id = ?;"
    cursor.execute(sql, params)

conn.commit()
conn.close()

print("✅ ซิงค์ agent_code ให้ตรงกับ assigned_agent_code และปรับสถานะเรียบร้อยแล้ว!")
