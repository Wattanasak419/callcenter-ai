import sqlite3, random
from pathlib import Path

db_path = Path("callcenter.db")
if not db_path.exists():
    db_path = Path("backend/callcenter.db")

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# 1. ตรวจสอบคอลัมน์ใน call_records
cursor.execute("PRAGMA table_info(call_records);")
cols = [r[1] for r in cursor.fetchall()]

# 2. ดูค่าตัวอย่างในคอลัมน์ที่น่าจะเป็นสถานะ
status_candidates = [c for c in cols if any(k in c.lower() for k in ["status", "stage", "state"])]
print("คอลัมน์สถานะที่พบ:", status_candidates)

# 3. ดึงเคสทั่วไปทั้งหมด (ไม่เอา Omazz)
cursor.execute("SELECT id FROM call_records WHERE brand IS NULL OR LOWER(brand) != 'omazz';")
all_general_ids = [r[0] for r in cursor.fetchall()]

print(f"กำลังอัปเดตสถานะให้ปิดเคสสำเร็จ 75% จากทั้งหมด {len(all_general_ids)} เคส...")

updated_count = 0
for cid in all_general_ids:
    is_resolved = random.random() < 0.75
    
    fields = []
    params = []
    
    # อัปเดตสถานะทั้งภาษาไทยและอังกฤษ เพื่อให้ครอบคลุมเงื่อนไขการ query ของระบบ
    thai_status = "ปิดเคสสำเร็จ" if is_resolved else "กำลังดำเนินการ"
    eng_status = "closed" if is_resolved else "in_progress"
    stage_val = "resolved" if is_resolved else "in_progress"
    
    for c in status_candidates:
        fields.append(f"{c} = ?")
        # ถ้าเป็นคอลัมน์ stage มักเป็น resolved ถ้า status มักเป็น ปิดเคสสำเร็จ หรือ closed
        if "stage" in c.lower():
            params.append(stage_val)
        else:
            params.append(thai_status)

    if "is_resolved" in cols:
        fields.append("is_resolved = ?")
        params.append(1 if is_resolved else 0)
    if "is_closed" in cols:
        fields.append("is_closed = ?")
        params.append(1 if is_resolved else 0)
    if "resolved" in cols:
        fields.append("resolved = ?")
        params.append(1 if is_resolved else 0)

    if fields:
        params.append(cid)
        cursor.execute(f"UPDATE call_records SET {', '.join(fields)} WHERE id = ?;", params)
        if is_resolved:
            updated_count += 1

conn.commit()
conn.close()

print(f"✅ เรียบร้อย! เปลี่ยนสถานะเป็น 'ปิดเคสสำเร็จ' แล้วจำนวน {updated_count} เคส")
