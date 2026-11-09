import sqlite3, random
from pathlib import Path

db_path = Path("callcenter.db")
if not db_path.exists():
    db_path = Path("backend/callcenter.db")

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# 1. ตรวจสอบคอลัมน์ทั้งหมดในตาราง call_records
cursor.execute("PRAGMA table_info(call_records);")
cols = [r[1] for r in cursor.fetchall()]

# 2. รายชื่อพนักงานสำหรับกระจายเคสทั่วไป (1-5)
cursor.execute("SELECT agent_code FROM agents WHERE agent_code IS NOT NULL AND agent_code != '';")
all_agents = [r[0] for r in cursor.fetchall()]
if not all_agents:
    all_agents = ['EXT401', 'EXT402', 'EXT403', 'EXT404', 'EXT405']
target_agents = all_agents[:5]

# 3. กำหนด 20 เคสแรกให้เป็น VVIP เท่านั้น (ไม่ด่วน / รอมอบหมาย)
cursor.execute("SELECT id FROM call_records ORDER BY id ASC LIMIT 20;")
vvip_ids = [r[0] for r in cursor.fetchall()]

for cid in vvip_ids:
    fields = ["brand = 'Omazz'"]
    params = []
    
    if "priority" in cols:
        fields.append("priority = 'vvip'")
    if "urgency" in cols:
        fields.append("urgency = 'normal'")
    if "is_urgent" in cols:
        fields.append("is_urgent = 0")
    if "sentiment" in cols:
        fields.append("sentiment = 'positive'")

    # เคลียร์ผู้ดูแลให้เป็น NULL เพื่อให้ขึ้นปุ่ม [มอบหมายงาน]
    if "assigned_agent_code" in cols:
        fields.append("assigned_agent_code = NULL")
    if "assigned_to" in cols:
        fields.append("assigned_to = NULL")
    if "handled_by" in cols:
        fields.append("handled_by = NULL")
        
    params.append(cid)
    cursor.execute(f"UPDATE call_records SET {', '.join(fields)} WHERE id = ?;", params)

# 4. เคสที่เหลือทั้งหมด -> ปลด URGENT ออกทั้งหมด ให้กลายเป็นเคสทั่วไป และสุ่มแจกให้พนักงาน 1-5
placeholders = ','.join(['?'] * len(vvip_ids))
cursor.execute(f"SELECT id FROM call_records WHERE id NOT IN ({placeholders}) ORDER BY id ASC;", vvip_ids)
general_ids = [r[0] for r in cursor.fetchall()]

GENERAL_BRANDS = ["Lotus", "Dunlopillo"]

for gid in general_ids:
    assigned = random.choice(target_agents)
    brand = random.choice(GENERAL_BRANDS)
    
    fields = ["brand = ?"]
    params = [brand]
    
    # ปลดสถานะด่วน / vvip ออกจากเคสทั่วไป
    if "priority" in cols:
        fields.append("priority = 'general'")
    if "urgency" in cols:
        fields.append("urgency = 'normal'")
    if "is_urgent" in cols:
        fields.append("is_urgent = 0")
    if "sentiment" in cols:
        fields.append("sentiment = 'neutral'")
        
    # มอบหมายให้พนักงาน 1-5
    if "assigned_agent_code" in cols:
        fields.append("assigned_agent_code = ?")
        params.append(assigned)
    if "assigned_to" in cols:
        fields.append("assigned_to = ?")
        params.append(assigned)
    if "handled_by" in cols:
        fields.append("handled_by = ?")
        params.append(assigned)
        
    params.append(gid)
    cursor.execute(f"UPDATE call_records SET {', '.join(fields)} WHERE id = ?;", params)

conn.commit()
conn.close()

print(f"\n✅ แยกสำเร็จเรียบร้อย!")
print(f"- เคส VVIP เหลือเพียง {len(vvip_ids)} เคส (รอมอบหมาย)")
print(f"- ปลดเคสด่วน (URGENT) ทั้งหมดออก และย้ายไปเป็นเคสทั่วไปจำนวน {len(general_ids)} เคส พร้อมแจกให้พนักงาน 1-5 เรียบร้อยครับ")
