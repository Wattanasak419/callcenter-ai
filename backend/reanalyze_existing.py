# backend/reanalyze_existing.py
import json
import sys
import os
import re

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.database import SessionLocal, engine
from backend.models import CallRecord
from transformers import pipeline

print("กำลังโหลดโมเดลประเมิน Sentiment บน GPU...")
classifier = pipeline(
    "sentiment-analysis",
    model="nlptown/bert-base-multilingual-uncased-sentiment",
    device=0
)

# คำบ่งบอกอารมณ์/ความรู้สึกในบริบท Call Center
POSITIVE_KEYWORDS = [
    "ขอบคุณ", "เรียบร้อย", "ดี", "พอใจ", "โอเค", "เข้าใจแล้ว", "รวดเร็ว",
    "ยอดเยี่ยม", "ช่วยเหลือดี", "สะดวก", "แก้ไขได้", "ตกลง"
]
NEGATIVE_KEYWORDS = [
    "พัง", "ชำรุด", "หัก", "ขาด", "แย่", "ช้า", "นาน", "ไม่พอใจ", "เสีย",
    "ปัญหา", "ร้องเรียน", "ไม่ได้เรื่อง", "ผิดหวัง", "ทะลุ", "ยุบ", "ไม่รับผิดชอบ"
]

def analyze_context_score(summary_text: str, convo_list: list) -> int:
    """วิเคราะห์คะแนนอิงจาก สรุปเคส และ ประโยคพูดคุยทั้งหมดจริง"""
    # 1. รวมข้อความทั้งหมดในเคส
    texts = []
    if summary_text:
        texts.append(summary_text)

    for item in convo_list:
        txt = item.get("text", "").strip() if isinstance(item, dict) else str(item).strip()
        if len(txt) > 3:
            texts.append(txt)

    full_context = " ".join(texts)
    if not full_context.strip():
        return 60

    # 2. ตรวจสอบคีย์เวิร์ดเชิงบวก / ลบ จากบริบทจริง
    pos_matches = sum(1 for kw in POSITIVE_KEYWORDS if kw in full_context)
    neg_matches = sum(1 for kw in NEGATIVE_KEYWORDS if kw in full_context)

    # 3. รันโมเดล Sentiment บนข้อความสรุปและประโยคสำคัญ
    sample_text = full_context[:512]
    try:
        res = classifier(sample_text)[0]
        label = res["label"]  # '1 star' ถึง '5 stars'
        model_stars = int(label.split()[0]) if label.split()[0].isdigit() else 3
    except Exception:
        model_stars = 3

    # แปลง model_stars เป็นฐานคะแนนเต็ม 100
    base_score = model_stars * 20

    # ปรับคะแนนตามบริบทจริงของปัญหาและคำขอบคุณ
    # - หากมีเรื่องสินค้าพัง/ชำรุด/ร้องเรียน คะแนนความพึงพอใจเริ่มต้นจะต่ำลง
    # - หากการสนทนามีคำขอบคุณหรือแก้ไขปัญหาได้ คะแนนจะขยับขึ้น
    score_adjustment = (pos_matches * 8) - (neg_matches * 10)
    final_score = base_score + score_adjustment

    # จำกัดให้อยู่ในช่วง 15 - 95 เพื่อความสมจริงตามเนื้อหา
    final_score = max(15, min(95, final_score))

    # ปรับให้เป็นเลขกลมๆ
    return int(round(final_score))


def run():
    db = SessionLocal()
    try:
        records = db.query(CallRecord).filter(
            CallRecord.is_active.is_(True)
        ).all()

        print(f"พบข้อมูลทั้งหมด {len(records)} รายการ กำลังเริ่มคำนวณคะแนนตามข้อมูลจริง...")

        updated_count = 0
        for r in records:
            convo = []
            if r.conversation_json:
                try:
                    convo = json.loads(r.conversation_json) if isinstance(r.conversation_json, str) else r.conversation_json
                except Exception:
                    convo = []

            # คำนวณคะแนนใหม่โดยอิงจาก summary, issue และบทสนทนาจริง
            summary_info = f"{r.issue or ''} {r.summary or ''}"
            new_score = analyze_context_score(summary_info, convo)

            old_score = r.sentiment_score
            r.sentiment_score = new_score
            updated_count += 1
            print(f"ID {r.id} ({r.customer_phone or 'No phone'}): คะแนนเดิม {old_score} -> วิเคราะห์ตามเนื้อหาได้ {new_score}/100")

        db.commit()
        print(f"\nอัปเดตข้อมูลเสร็จสิ้น {updated_count} รายการ เรียบร้อยแล้ว")
    except Exception as e:
        db.rollback()
        print(f"เกิดข้อผิดพลาด: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    run()