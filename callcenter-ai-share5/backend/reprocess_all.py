# reprocess_all.py
import os
from backend.database import SessionLocal
from backend.models import CallRecord

db = SessionLocal()
records = db.query(CallRecord).filter(CallRecord.is_active == True).all()

# รีเซ็ตสถานะเป็น pending ทั้งหมด
for r in records:
    r.status = "pending"

db.commit()
db.close()
print(f"รีเซ็ตเคสทั้งหมด {len(records)} รายการเป็น 'pending' เรียบร้อยแล้ว เมื่อ Restart Backend ระบบจะรันใหม่ให้อัตโนมัติ")