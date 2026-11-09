import sqlite3
from pathlib import Path

db_path = Path("callcenter.db")
if not db_path.exists():
    db_path = Path("backend/callcenter.db")

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# 1. ตรวจสอบคอลัมน์ใน call_records
cursor.execute("PRAGMA table_info(call_records);")
cols = [r[1] for r in cursor.fetchall()]

# 2. คัดเลือกเฉพาะ 20 เคสแรกให้เป็น VVIP
cursor.execute("SELECT id FROM call_records ORDER BY id ASC LIMIT 20;")
vvip_ids = [r[0] for r in cursor.fetchall()]

# 3. อัปเดต 20 เคสแรกให้เป็น VVIP และล้างค่าผู้ดูแลเพื่อให้คุณมากดเลือกเองที่หน้าเว็บ
for cid in vvip_ids:
    fields = ["brand = 'Omazz'"]
    params = []
    
    if "priority" in cols:
        fields.append("priority = 'vvip'")
    if "urgency" in cols:
        fields.append("urgency = 'normal'")
    if "is_urgent" in cols:
        fields.append("is_urgent = 0")
        
    # เคลียร์ผู้ดูแลให้ขึ้น "รอมอบหมาย" เพื่อให้คุณกดเลือกที่ปุ่มหน้าเว็บเอง
    if "assigned_agent_code" in cols:
        fields.append("assigned_agent_code = NULL")
    if "assigned_to" in cols:
        fields.append("assigned_to = NULL")
    if "handled_by" in cols:
        fields.append("handled_by = NULL")
        
    params.append(cid)
    cursor.execute(f"UPDATE call_records SET {', '.join(fields)} WHERE id = ?;", params)

# 4. เคสที่เหลือทั้งหมด -> ปลด URGENT ออก และตั้งให้เป็นเคสทั่วไป (general) ทั้งหมด
placeholders = ','.join(['?'] * len(vvip_ids))
gen_fields = ["brand = 'Lotus'"]

if "priority" in cols:
    gen_fields.append("priority = 'general'")
if "urgency" in cols:
    gen_fields.append("urgency = 'normal'")
if "is_urgent" in cols:
    gen_fields.append("is_urgent = 0")

sql_clean_others = f"UPDATE call_records SET {', '.join(gen_fields)} WHERE id NOT IN ({placeholders});"
cursor.execute(sql_clean_others, vvip_ids)

conn.commit()
conn.close()

print(f"✅ สำเร็จ!")
print(f"- ปรับเคส VVIP ให้เหลือเฉพาะ 20 เคสแรก ({len(vvip_ids)} เคส) และเคลียร์ให้ขึ้น 'รอมอบหมาย' ทั้งหมด")
print(f"- เคสที่เหลือถูกปลดสถานะ URGENT ออก และปรับเป็นเคสทั่วไปเรียบร้อยแล้ว (จะไม่มาโผล่ปนในหน้านี้อีก)")
