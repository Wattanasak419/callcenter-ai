import csv
from backend.database import SessionLocal
from backend.models import Agent

db = SessionLocal()
csv_file_path = "employees.csv"  # เปลี่ยนชื่อให้ตรงกับไฟล์ CSV ของคุณ

with open(csv_file_path, mode="r", encoding="utf-8") as f:
  reader = csv.DictReader(f)
  for row in reader:
    ext = row["Extension Number"].strip()
    caller_id = row["Caller ID Name"].strip()  # เช่น "CS วุฒิ นางเลิ้ง"
    user_role = row.get("User Role", "").strip()

    # แยกคำนำหน้า, ชื่อ, และสถานที่ (สาขา)
    parts = caller_id.split()
    first_name = parts[1] if len(parts) > 1 else caller_id
    last_name = parts[2] if len(parts) > 2 else ""

    # กำหนด role ตาม User Role ในตาราง
    role = (
        "supervisor"
        if "Administrator" in user_role or "Admin" in user_role
        else "staff"
    )

    agent_code = f"EXT{ext}"

    # ตรวจสอบว่ามีข้อมูลเดิมอยู่แล้วหรือไม่
    agent = db.query(Agent).filter(Agent.agent_code == agent_code).first()

    if not agent:
      agent = Agent(
          agent_code=agent_code,
          password=ext,  # ตั้งรหัสผ่านเริ่มต้นเป็นเบอร์ Extension
          firstname=first_name,
          lastname=last_name,
          role=role,
          phone=ext,
          department="Customer Service",
          position=caller_id,
      )
      db.add(agent)
    else:
      # อัปเดตข้อมูลหากมีอยู่แล้ว
      agent.firstname = first_name
      agent.lastname = last_name
      agent.role = role
      agent.position = caller_id

db.commit()
db.close()
print("นำเข้ารายชื่อพนักงานจาก CSV เข้าสู่ฐานข้อมูลเรียบร้อยแล้ว!")