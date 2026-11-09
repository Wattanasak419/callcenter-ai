import sqlite3, random
from pathlib import Path
from datetime import datetime, timedelta

db_path = Path("callcenter.db")
if not db_path.exists():
    db_path = Path("backend/callcenter.db")

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# 1. รายชื่อลูกค้า VVIP 5 ท่านพร้อมเบอร์ประจำตัว (โทรซ้ำคนละ ~4 เคส)
VVIP_CUSTOMERS = [
    {"name": "กรณ์ จิรวัฒน์โกวิท", "phone": "0819998821", "addr": "99/12 หมู่ 2 ต.สุเทพ อ.เมืองเชียงใหม่ เชียงใหม่ 50200"},
    {"name": "พิชญ์สิณี เตชะไพบูลย์", "phone": "0898881234", "addr": "14/2 ถนนเทพกระษัตรี ต.ตลาดใหญ่ อ.เมืองภูเก็ต ภูเก็ต 83000"},
    {"name": "เศรษฐพงศ์ รัตนโชติ", "phone": "0637775512", "addr": "77/2 หมู่ 6 ถนนมิตรภาพ ต.ในเมือง อ.เมืองขอนแก่น ขอนแก่น 40000"},
    {"name": "พิมพ์ลภัส วัฒนพาณิชย์", "phone": "0946663390", "addr": "89/15 หมู่ 9 ต.หนองปรือ อ.บางละมุง ชลบุรี 20150"},
    {"name": "วรภัทร กิตติคุณไพศาล", "phone": "0825554411", "addr": "150/4 ถนนเพชรเกษม ต.หัวหิน อ.หัวหิน ประจวบคีรีขันธ์ 77110"}
]

# 2. รายชื่อพนักงาน
cursor.execute("SELECT agent_code FROM agents WHERE agent_code IS NOT NULL AND agent_code != '';")
agents = [r[0] for r in cursor.fetchall()]
if not agents:
    agents = ['EMP001', 'EMP002', 'EMP003', 'EXT101', 'EXT102', 'EXT103']

cursor.execute("PRAGMA table_info(call_records);")
cols = [r[1] for r in cursor.fetchall()]

# 3. สุ่มเลือก 20 เคสเพื่อแปลงเป็น VVIP (Omazz)
cursor.execute("SELECT id FROM call_records ORDER BY id ASC;")
all_ids = [r[0] for r in cursor.fetchall()]
random.shuffle(all_ids)
vvip_case_ids = all_ids[:20]

print(f"กำลังแปลงเคสจำนวน {len(vvip_case_ids)} เคส ให้เป็น VVIP (Omazz)...")

for idx, case_id in enumerate(vvip_case_ids):
    cust = VVIP_CUSTOMERS[idx % len(VVIP_CUSTOMERS)]
    assigned = agents[idx % len(agents)]
    is_resolved = random.random() < 0.8
    
    fn_ln = cust["name"].split(" ", 1)
    fn = fn_ln[0]
    ln = fn_ln[1] if len(fn_ln) > 1 else ""

    fields = [
        "brand = 'Omazz'",
        "customer_phone = ?",
        "firstname = ?",
        "lastname = ?",
        "assigned_agent_code = ?",
        "status = 'done'"
    ]
    params = [cust["phone"], fn, ln, assigned]

    if "priority" in cols:
        fields.append("priority = 'vvip'")
    if "handled_by" in cols:
        fields.append("handled_by = ?")
        params.append(assigned)
    if "case_stage" in cols:
        fields.append("case_stage = ?")
        params.append("resolved" if is_resolved else "in_progress")
    if "closed_by" in cols:
        fields.append("closed_by = ?")
        params.append(assigned if is_resolved else None)
    if "address" in cols:
        fields.append("address = ?")
        params.append(cust["addr"])

    params.append(case_id)
    sql = f"UPDATE call_records SET {', '.join(fields)} WHERE id = ?;"
    cursor.execute(sql, params)

conn.commit()
conn.close()
print(f"✅ สำเร็จ! แยกเคส VVIP (Omazz) เรียบร้อย 20 เคส จากลูกค้า 5 ท่าน (ท่านละ 4 เคส)")
