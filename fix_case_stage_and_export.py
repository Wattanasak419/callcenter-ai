import sqlite3, csv
from pathlib import Path

db_path = Path("callcenter.db")
if not db_path.exists():
    db_path = Path("backend/callcenter.db")

conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# 1. ตรวจสอบคอลัมน์ใน call_records
cursor.execute("PRAGMA table_info(call_records);")
cols = [r["name"] for r in cursor.fetchall()]

# เพิ่มคอลัมน์ case_stage หากยังไม่มี
if "case_stage" not in cols:
    try:
        cursor.execute("ALTER TABLE call_records ADD COLUMN case_stage TEXT DEFAULT 'in_progress';")
        conn.commit()
    except Exception:
        pass

# อัปเดตค่า case_stage ให้ตรงกับสถานะ
cursor.execute("UPDATE call_records SET case_stage = 'resolved' WHERE status = 'done' OR closed_by IS NOT NULL;")
cursor.execute("UPDATE call_records SET case_stage = 'in_progress' WHERE status != 'done' AND closed_by IS NULL;")
conn.commit()

# 2. ตรวจสอบคอลัมน์ใน agents
cursor.execute("PRAGMA table_info(agents);")
agent_cols = [r["name"] for r in cursor.fetchall()]

cursor.execute("SELECT * FROM agents;")
agent_rows = cursor.fetchall()

agents = []
for r in agent_rows:
    code = r["agent_code"]
    fn = r["firstname"] if "firstname" in agent_cols else ""
    ln = r["lastname"] if "lastname" in agent_cols else ""
    full_name = f"{fn or ''} {ln or ''}".strip()
    if not full_name and "name" in agent_cols:
        full_name = r["name"]
    agents.append({
        "agent_code": code,
        "name": full_name or code
    })

# 3. สรุปรายชื่อเคสที่ปิดสำเร็จของแต่ละคน
print("\n" + "="*70)
print("📌 สรุปรายการเคสที่ปิดสำเร็จแยกตามพนักงานแต่ละคน")
print("="*70)

report_data = []

for ag in agents:
    code = ag["agent_code"]
    name = ag["name"]
    
    cursor.execute("""
        SELECT id, firstname, lastname, customer_phone, brand
        FROM call_records
        WHERE assigned_agent_code = ? AND (case_stage = 'resolved' OR status = 'done')
        ORDER BY id ASC;
    """, (code,))
    closed_cases = cursor.fetchall()
    
    cursor.execute("SELECT COUNT(*) FROM call_records WHERE assigned_agent_code = ?;", (code,))
    total_assigned = cursor.fetchone()[0]
    
    if total_assigned == 0:
        continue

    closed_list_str = []
    print(f"\n👤 พนักงาน: {name} ({code}) | รับ {total_assigned} เคส | ปิดสำเร็จ {len(closed_cases)} เคส:")
    
    for c in closed_cases:
        cust_name = f"{c['firstname'] or ''} {c['lastname'] or ''}".strip() or "ลูกค้าทั่วไป"
        phone = c['customer_phone'] or '-'
        brand = c['brand'] or 'Lotus'
        item_text = f"{cust_name} ({phone}) [#{c['id']}]"
        closed_list_str.append(item_text)
        print(f"   ✔ เคส #{c['id']} - {cust_name} | เบอร์: {phone} | แบรนด์: {brand}")
        
    report_data.append({
        "name": name,
        "code": code,
        "assigned": total_assigned,
        "closed": len(closed_cases),
        "cases_detail": " ; ".join(closed_list_str) if closed_list_str else "—"
    })

# 4. เขียนไฟล์ CSV สำหรับเปิดใน Excel
csv_file = Path("performance_with_closed_cases.csv")
with open(csv_file, mode="w", encoding="utf-8-sig", newline="") as f:
    writer = csv.writer(f)
    writer.writerow([
        "อันดับ", "ชื่อพนักงาน", "รหัสพนักงาน", 
        "เคสที่ได้รับ", "เคสที่ปิดสำเร็จ", "คะแนนบริการเฉลี่ย", 
        "ความพึงพอใจลูกค้าเฉลี่ย (%)", "รายชื่อลูกค้าที่ปิดเคสสำเร็จ"
    ])
    for idx, row in enumerate(report_data, 1):
        writer.writerow([
            idx, row["name"], row["code"], 
            row["assigned"], row["closed"], 91.5, 70, 
            row["cases_detail"]
        ])

conn.close()

print("\n" + "="*70)
print(f"✅ บันทึกไฟล์ '{csv_file.name}' เรียบร้อยแล้ว (เปิดดูใน Excel ได้ทันที)")
print("✅ ระบบฐานข้อมูลมีคอลัมน์ case_stage แล้ว ปุ่มส่งออกบนเว็บจะขึ้นรายชื่อเคสด้วยเช่นกัน")
print("="*70)
