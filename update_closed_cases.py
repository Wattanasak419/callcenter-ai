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

# 2. ตรวจสอบคอลัมน์ใน agents
cursor.execute("PRAGMA table_info(agents);")
agent_cols = [r[1] for r in cursor.fetchall()]

agent_map = {}
if "agent_code" in agent_cols and ("name" in agent_cols or "agent_name" in agent_cols):
    name_col = "name" if "name" in agent_cols else "agent_name"
    cursor.execute(f"SELECT agent_code, {name_col} FROM agents;")
    for code, name in cursor.fetchall():
        if code:
            agent_map[code] = name

# 3. ระบุคอลัมน์สำหรับรหัสพนักงาน
agent_id_col = None
for candidate in ["assigned_agent_code", "assigned_to", "agent_code"]:
    if candidate in cols:
        agent_id_col = candidate
        break

# เงื่อนไขกรองไม่เอาเคส VVIP (ตรวจสอบว่ามีคอลัมน์ใดให้กรองบ้าง)
where_conds = []
if agent_id_col:
    where_conds.append(f"{agent_id_col} IS NOT NULL")
if "brand" in cols:
    where_conds.append("(brand IS NULL OR LOWER(brand) != 'omazz')")
if "priority" in cols:
    where_conds.append("(priority IS NULL OR LOWER(priority) != 'vvip')")

where_clause = " AND ".join(where_conds) if where_conds else "1=1"

select_cols = f"id, {agent_id_col}" if agent_id_col else "id"
cursor.execute(f"SELECT {select_cols} FROM call_records WHERE {where_clause};")
rows = cursor.fetchall()

assigned_cases = [(r[0], r[1] if agent_id_col else "EXT101") for r in rows]
print(f"กำลังประมวลผลอัปเดตยอดปิดเคสสำหรับ {len(assigned_cases)} เคส...")

# 4. อัปเดตสถานะการปิดเคส
for case_id, agent_code in assigned_cases:
    is_closed = random.random() < 0.75
    agent_name = agent_map.get(agent_code, agent_code)

    fields = []
    params = []

    if "status" in cols:
        fields.append("status = ?")
        params.append("closed" if is_closed else "in_progress")

    if "case_stage" in cols:
        fields.append("case_stage = ?")
        params.append("resolved" if is_closed else "in_progress")

    if "is_resolved" in cols:
        fields.append("is_resolved = ?")
        params.append(1 if is_closed else 0)

    if "is_closed" in cols:
        fields.append("is_closed = ?")
        params.append(1 if is_closed else 0)

    if "resolved" in cols:
        fields.append("resolved = ?")
        params.append(1 if is_closed else 0)

    if "closed_by" in cols:
        fields.append("closed_by = ?")
        params.append(agent_code if is_closed else None)

    if "resolved_by" in cols:
        fields.append("resolved_by = ?")
        params.append(agent_code if is_closed else None)

    if "handled_by" in cols:
        fields.append("handled_by = ?")
        params.append(agent_name)

    if fields:
        params.append(case_id)
        cursor.execute(f"UPDATE call_records SET {', '.join(fields)} WHERE id = ?;", params)

conn.commit()
conn.close()

print("✅ อัปเดตสถานะการปิดเคสสำเร็จเรียบร้อย!")
