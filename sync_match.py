import sqlite3, random
from pathlib import Path

db_path = Path("callcenter.db")
if not db_path.exists():
    db_path = Path("backend/callcenter.db")

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# 1. ดึงพนักงานทั้งหมด
cursor.execute("SELECT agent_code FROM agents WHERE agent_code IS NOT NULL AND agent_code != '';")
agents = [r[0] for r in cursor.fetchall()]
if not agents:
    agents = ['EMP001', 'EMP002', 'EMP003', 'EXT101', 'EXT102', 'EXT103']

cursor.execute("PRAGMA table_info(call_records);")
cols = [r[1] for r in cursor.fetchall()]

# 2. ปรับเคสทั้งหมดให้เป็นลูกค้าทั่วไป (Lotus) ก่อน
cursor.execute("UPDATE call_records SET brand = 'Lotus';")

# 3. สุ่มเลือก 20 เคสเป็น VVIP (Omazz) แน่นอน
VVIP_CUSTOMERS = [
    {"name": "กรณ์ จิรวัฒน์โกวิท", "phone": "0819998821"},
    {"name": "พิชญ์สิณี เตชะไพบูลย์", "phone": "0898881234"},
    {"name": "เศรษฐพงศ์ รัตนโชติ", "phone": "0637775512"},
    {"name": "พิมพ์ลภัส วัฒนพาณิชย์", "phone": "0946663390"},
    {"name": "วรภัทร กิตติคุณไพศาล", "phone": "0825554411"}
]

cursor.execute("SELECT id FROM call_records ORDER BY id ASC;")
all_ids = [r[0] for r in cursor.fetchall()]
random.shuffle(all_ids)

vvip_ids = all_ids[:20]
general_ids = all_ids[20:]

# อัปเดตเคส VVIP 20 เคส
for idx, cid in enumerate(vvip_ids):
    cust = VVIP_CUSTOMERS[idx % len(VVIP_CUSTOMERS)]
    ag = agents[idx % len(agents)]
    fn, ln = cust["name"].split(" ", 1)
    
    fields = [
        "brand = 'Omazz'",
        "customer_phone = ?",
        "firstname = ?",
        "lastname = ?",
        "assigned_agent_code = ?",
        "status = 'done'"
    ]
    params = [cust["phone"], fn, ln, ag]
    if "handled_by" in cols:
        fields.append("handled_by = ?")
        params.append(ag)
    if "priority" in cols:
        fields.append("priority = 'vvip'")
    params.append(cid)
    cursor.execute(f"UPDATE call_records SET {', '.join(fields)} WHERE id = ?;", params)

# อัปเดตเคสทั่วไปที่เหลือให้กระจายพนักงานเท่าๆ กัน
for idx, cid in enumerate(general_ids):
    ag = agents[idx % len(agents)]
    fields = [
        "assigned_agent_code = ?",
        "status = 'done'"
    ]
    params = [ag]
    if "handled_by" in cols:
        fields.append("handled_by = ?")
        params.append(ag)
    if "priority" in cols:
        fields.append("priority = 'normal'")
    params.append(cid)
    cursor.execute(f"UPDATE call_records SET {', '.join(fields)} WHERE id = ?;", params)

conn.commit()
conn.close()
print("✅ ซิงค์ฐานข้อมูลเชื่อมต่อ VVIP 20 เคส และทั่วไปเรียบร้อยแล้ว!")
