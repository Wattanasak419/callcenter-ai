import sqlite3, random
from pathlib import Path

db_path = Path("callcenter.db")
if not db_path.exists():
    db_path = Path("backend/callcenter.db")

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# 1. ดึงรายชื่อพนักงานทั้งหมด
cursor.execute("SELECT agent_code FROM agents WHERE agent_code IS NOT NULL AND agent_code != '';")
agents = [r[0] for r in cursor.fetchall()]
if not agents:
    agents = ['EXT401', 'EXT402', 'EXT403', 'EXT406']

# 2. ตรวจสอบคอลัมน์ใน call_records
cursor.execute("PRAGMA table_info(call_records);")
cols = [r[1] for r in cursor.fetchall()]

# 3. ดึงเฉพาะ "เคสทั่วไป" (ไม่เอา Omazz และไม่เอา vvip)
where_clauses = ["(brand IS NULL OR LOWER(brand) != 'omazz')"]
if "priority" in cols:
    where_clauses.append("(priority IS NULL OR LOWER(priority) != 'vvip')")

sql_get_general = f"SELECT id FROM call_records WHERE {' AND '.join(where_clauses)} ORDER BY id ASC;"
cursor.execute(sql_get_general)
general_cases = [r[0] for r in cursor.fetchall()]

print(f"พบเคสทั่วไปทั้งหมด {len(general_cases)} เคส (ข้ามเคส VVIP 20 เคสเดิมเรียบร้อย)")
print(f"กำลังกระจายเคสทั่วไปให้พนักงาน {len(agents)} คน...")

random.shuffle(general_cases)

# รายชื่อลูกค้าทั่วไปสำหรับใส่ข้อมูลจำลอง (Lotus / Dunlopillo)
GENERAL_CUSTOMERS = [
    {"name": "สมชาย ยิ่งยง", "phone": "0812345678", "brand": "Lotus"},
    {"name": "กรรณิการ์ สุขใจ", "phone": "0891234567", "brand": "Lotus"},
    {"name": "ประสิทธิ์ มั่งคั่ง", "phone": "0867891234", "brand": "Dunlopillo"},
    {"name": "วิภาดา ศรีสุข", "phone": "0912345678", "brand": "Lotus"},
    {"name": "ธนพล เจริญสุข", "phone": "0845678901", "brand": "Dunlopillo"}
]

# 4. กระจายเคสทั่วไปให้พนักงาน
for idx, case_id in enumerate(general_cases):
    assigned = agents[idx % len(agents)]
    cust = GENERAL_CUSTOMERS[idx % len(GENERAL_CUSTOMERS)]
    fn, ln = cust["name"].split(" ", 1)
    
    # กำหนดให้ปิดเคสสำเร็จประมาณ 75% ที่เหลืออยู่ระหว่างดำเนินการ (in_progress)
    is_resolved = random.random() < 0.75

    fields = [
        "assigned_agent_code = ?",
        "brand = ?"
    ]
    params = [assigned, cust["brand"]]

    if "firstname" in cols:
        fields.append("firstname = ?")
        params.append(fn)
    if "lastname" in cols:
        fields.append("lastname = ?")
        params.append(ln)
    if "customer_phone" in cols:
        fields.append("customer_phone = ?")
        params.append(cust["phone"])
    if "handled_by" in cols:
        fields.append("handled_by = ?")
        params.append(assigned)
    if "priority" in cols:
        fields.append("priority = 'general'")
    if "case_stage" in cols:
        fields.append("case_stage = ?")
        params.append("resolved" if is_resolved else "in_progress")
    if "status" in cols:
        fields.append("status = ?")
        params.append("closed" if is_resolved else "in_progress")
    if "closed_by" in cols:
        fields.append("closed_by = ?")
        params.append(assigned if is_resolved else None)

    params.append(case_id)
    sql_update = f"UPDATE call_records SET {', '.join(fields)} WHERE id = ?;"
    cursor.execute(sql_update, params)

conn.commit()
conn.close()

print(f"✅ สำเร็จ! อัปเดตและกระจายเคสทั่วไป {len(general_cases)} เคส ให้พนักงาน {len(agents)} คนเรียบร้อย (เคส VVIP ยังอยู่ครบเหมือนเดิม)")
