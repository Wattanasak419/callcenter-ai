from pathlib import Path
from datetime import datetime
from backend.database import SessionLocal
from backend.models import CallRecord

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"

db = SessionLocal()

# สแกนหาไฟล์ทั้งหมดในโฟลเดอร์ uploads
count = 0
for file_path in UPLOAD_DIR.glob("*.*"):
    filename = file_path.name
    
    # ข้ามไฟล์ระบบหรือไฟล์ที่ไม่เกี่ยวข้อง
    if filename.startswith("manual_") or filename.endswith(".tmp"):
        continue
        
    # เช็กว่ามีชื่อไฟล์นี้อยู่ในฐานข้อมูลหรือยัง
    existing = db.query(CallRecord).filter(CallRecord.filename == filename).first()
    if not existing:
        # ถ้ายังไม่มี ให้สร้างข้อมูลจำลองเพื่อให้ตารางบนเว็บดึงไปแสดงผลได้
        new_record = CallRecord(
            filename=filename,
            customer_phone="0812345678", # กำหนดเบอร์โทรสำรอง
            direction="Inbound",
            status="done",
            sentiment_score=4.0,
            issue="กู้คืนข้อมูลจากระบบอัตโนมัติ",
            summary="ข้อมูลเสียงถูกดึงกลับคืนจากการสแกนเซิร์ฟเวอร์",
            file_hash=filename,
            created_at=datetime.now()
        )
        db.add(new_record)
        count += 1

db.commit()
db.close()
print(f"กู้คืนข้อมูลเข้าฐานข้อมูลสำเร็จทั้งหมด {count} รายการ!")