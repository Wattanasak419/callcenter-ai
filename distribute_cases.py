import sqlite3, random
from pathlib import Path

db_path = Path("callcenter.db")
if not db_path.exists():
    db_path = Path("backend/callcenter.db")

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# 1. ตรวจสอบคอลัมน์ทั้งหมดใน call_records
cursor.execute("PRAGMA table_info(call_records);")
cols = [r[1] for r in cursor.fetchall()]

# 2. ดึงรายชื่อพนักงาน 5 คนแรกจากระบบ
cursor.execute("SELECT agent_code FROM agents WHERE agent_code IS NOT NULL AND agent_code != '';")
all_agents = [r[0] for r in cursor.fetchall()]
if not all_agents:
    all_agents = ['EXT401', 'EXT402', 'EXT403', 'EXT404', 'EXT405']

# ใช้พนักงาน 1-5 คนแรก
target_agents = all_agents[:5]
print(f"👉 รายชื่อพนักงาน 1-5 ที่จะกระจายเคสทั่วไป: {', '.join(target_agents)}")

# 3. กำหนด 20 เคสแรกให้เป็น VVIP และเว้นไว้ให้คุณมากดมอบหมายเองที่หน้าเว็บ
cursor.execute("SELECT id FROM call_records ORDER BY id ASC LIMIT 20;")
vvip_case_ids = [r[0] for r in cursor.fetchall()]

# ปรับ 20 เคสนี้ให้เป็น VVIP และแบรนด์ Omazz (คงสถานะรอคุณมากดมอบหมายเอง)
for cid in vvip_case_ids:
    fields = ["brand = 'Omazz'"]
    params = []
    if "priority" in cols:
        fields.append("priority = 'vvip'")
    params.append(cid)
    cursor.execute(f"UPDATE call_records SET {', '.join(fields)} WHERE id = ?;", params)

print(f"✅ ตั้งค่าเคส VVIP จำนวน {len(vvip_case_ids)} เคสเรียบร้อย (เว้นว่างไว้ให้คุณเลือกผู้ดูแลเองผ่านหน้าเว็บ)")

# 4. ดึงเคสที่เหลือทั้งหมด เพื่อแปลงเป็นเคสทั่วไป
placeholders = ','.join(['?'] * len(vvip_case_ids))
cursor.execute(f"SELECT id FROM call_records WHERE id NOT IN ({placeholders}) ORDER BY id ASC;", vvip_case_ids)
general_cases = [r[0] for r in cursor.fetchall()]

print(f"👉 กำลังกระจายเคสทั่วไปที่เหลือทั้งหมด {len(general_cases)} เคส ให้พนักงาน 1-5 แบบสุ่ม...")

GENERAL_CUSTOMERS = [
    {"name": "สมชาย ยิ่งยง", "phone": "0812345678", "brand": "Lotus"},
    {"name": "กรรณิการ์ สุขใจ", "phone": "0891234567", "brand": "Lotus"},
    {"name": "ประสิทธิ์ มั่งคั่ง", "phone": "0867891234", "brand": "Dunlopillo"},
    {"name": "วิภาดา ศรีสุข", "phone": "0912345678", "brand": "Lotus"},
    {"name": "ธนพล เจริญสุข", "phone": "0845678901", "brand": "Dunlopillo"}
]

random.shuffle(general_cases)

# 5. กระจายเคสทั่วไปให้พนักงาน 1-5 แบบสุ่ม พร้อมอัปเดตทุกฟิลด์ที่เกี่ยวข้อง
for case_id in general_cases:
    assigned = random.choice(target_agents)
    cust = random.choice(GENERAL_CUSTOMERS)
    fn, ln = cust["name"].split(" ", 1)
    is_resolved = random.random() < 0.75

    fields = ["brand = ?"]
    params = [cust["brand"]]

    # อัปเดตช่องรหัส/ชื่อพนักงานผู้ดูแลให้ครบทุกรูปแบบที่หน้าบ้านอาจใช้อ้างอิง
    if "assigned_agent_code" in cols:
        fields.append("assigned_agent_code = ?")
        params.append(assigned)
    if "assigned_to" in cols:
        fields.append("assigned_to = ?")
        params.append(assigned)
    if "agent_code" in cols:
        fields.append("agent_code = ?")
        params.append(assigned)
    if "handled_by" in cols:
        fields.append("handled_by = ?")
        params.append(assigned)

    # ข้อมูลลูกค้า
    if "firstname" in cols:
        fields.append("firstname = ?")
        params.append(fn)
    if "lastname" in cols:
        fields.append("lastname = ?")
        params.append(ln)
    if "customer_name" in cols:
        fields.append("customer_name = ?")
        params.append(cust["name"])
    if "customer_phone" in cols:
        fields.append("customer_phone = ?")
        params.append(cust["phone"])

    # ลำดับความสำคัญ และสถานะเคส
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
    cursor.execute(f"UPDATE call_records SET {', '.join(fields)} WHERE id = ?;", params)

conn.commit()
conn.close()

print(f"\n🎉 สำเร็จสมบูรณ์!")
print(f"- เคสทั่วไปจำนวน {len(general_cases)} เคส ถูกกระจายสุ่มให้พนักงาน 1-5 เรียบร้อย")
print(f"- คุณสามารถกดปุ่ม [+ มอบหมายงาน] ในหน้าเว็บเพื่อเลือกผู้ดูแลเคส VVIP เองได้ตามต้องการครับ")
