from backend.database import SessionLocal
from backend.models import CallRecord

db = SessionLocal()

# ค้นหาทุกรายการในฐานข้อมูล แล้วเปลี่ยนสถานะกลับเป็น 'done' ทั้งหมด
records = db.query(CallRecord).all()
count = 0
for record in records:
    record.status = "done"
    count += 1

db.commit()
db.close()
print(f"บังคับกู้คืนข้อมูลทั้งหมดกลับมาสำเร็จ {count} รายการ!")