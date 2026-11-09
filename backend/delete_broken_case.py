import os
import sys

# เพิ่มโฟลเดอร์หลักเข้า sys.path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
sys.path.insert(0, PROJECT_ROOT)
sys.path.insert(0, CURRENT_DIR)

try:
  from backend.database import SessionLocal
  from backend.models import CallRecord
except ModuleNotFoundError:
  from database import SessionLocal
  from models import CallRecord

# ค้นหาด้วยรหัสไฟล์ที่มีปัญหา
TARGET_HASH = '23f5e9b762dd4fcd8e6a08a5511c0b80'
UPLOAD_DIR = os.path.join(CURRENT_DIR, 'uploads')

db = SessionLocal()
try:
  record = (
      db.query(CallRecord)
      .filter(CallRecord.filename.like(f'%{TARGET_HASH}%'))
      .first()
  )

  if record:
    rec_id = record.id
    fname = record.filename

    # ลบออกจากฐานข้อมูล
    db.delete(record)
    db.commit()
    print(f'🗑️ ลบจากฐานข้อมูลสำเร็จ: Record ID {rec_id} ({fname})')

    # ลบไฟล์เสียงจริง
    file_path = os.path.join(UPLOAD_DIR, fname)
    if os.path.exists(file_path):
      os.remove(file_path)
      print(f'🗑️ ลบไฟล์เสียงสำเร็จ: {file_path}')
    else:
      print(f'ℹ️ ไม่พบไฟล์เสียงที่โฟลเดอร์ uploads')
  else:
    print('⚠️ ไม่พบเคสนี้ในฐานข้อมูล')

except Exception as e:
  db.rollback()
  print(f'❌ ผิดพลาด: {e}')
finally:
  db.close()