import os
import sys
import json

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.database import SessionLocal
from backend.models import CallRecord

# คำบ่งบอกพฤติกรรมที่ดีและสุภาพของพนักงาน
POLITE_WORDS = ["สวัสดี", "ยินดี", "ขออนุญาต", "รบกวน", "ขอบคุณ", "ครับ", "ค่ะ", "ยินดีบริการ"]
PROCEDURE_WORDS = ["ตรวจสอบ", "ประสานงาน", "ดำเนินการ", "ส่งเรื่อง", "ข้อมูล", "นัดหมาย", "สอบถาม", "ช่วยเหลือ", "โอนสาย"]
NEGATIVE_WORDS = ["ไม่รู้", "ไม่ว่าง", "ไม่ทำ", "ตัดสาย", "ไม่ได้เรื่อง", "รำคาญ"]

def evaluate_agent_score(conversation, action_taken, summary, sat_score, anomaly_flag) -> int:
    """
    คำนวณคะแนนพนักงาน (Agent Score) เต็ม 100:
    - อิงจากประโยคที่พนักงานพูดจริง
    - การ Take Action
    - ความพึงพอใจของลูกค้า (Satisfaction Score)
    - การตรวจพบข้อผิดพลาด/คำไม่สุภาพ
    """
    agent_texts = []
    
    # 1. รวบรวมข้อความเฉพาะฝั่งพนักงาน
    if isinstance(conversation, list):
        for item in conversation:
            if isinstance(item, dict):
                speaker = str(item.get("speaker", ""))
                text = str(item.get("text", ""))
                if any(k in speaker for k in ["พนักงาน", "Agent", "agent", "เจ้าหน้าที่"]):
                    agent_texts.append(text)
    
    agent_full_text = " ".join(agent_texts)
    
    # หากไม่มีแยกฝั่งพนักงานชัดเจน ให้ใช้ action_taken + summary ร่วมด้วย
    context = f"{agent_full_text} {action_taken or ''} {summary or ''}"
    
    # 2. ฐานคะแนนอิงจากความสำเร็จในการดูแลลูกค้า (Correlation กับ Satisfaction Score)
    # คะแนนความพึงพอใจลูกค้าส่งผลต่อประสิทธิภาพพนักงาน 40%
    base_score = 50 + (sat_score * 0.3)
    
    # 3. ตรวจสอบความสุภาพ (Politeness)
    polite_count = sum(1 for kw in POLITE_WORDS if kw in context)
    polite_bonus = min(15, polite_count * 3)
    
    # 4. ตรวจสอบการทำตามขั้นตอนและการแก้ปัญหา (Procedure & Action)
    proc_count = sum(1 for kw in PROCEDURE_WORDS if kw in context)
    proc_bonus = min(15, proc_count * 2.5)
    
    # มีบันทึก Action Taken ชัดเจน
    action_bonus = 5 if (action_taken and len(action_taken) > 5) else 0
    
    # 5. หักคะแนนหากมีคำลบ หรือติด Anomaly flag
    penalty = 0
    if anomaly_flag == 'yes':
        penalty += 20
    neg_count = sum(1 for kw in NEGATIVE_WORDS if kw in context)
    penalty += (neg_count * 10)
    
    # รวมคะแนน
    final_score = base_score + polite_bonus + proc_bonus + action_bonus - penalty
    
    # ควบคุมช่วงคะแนนให้อยู่ระหว่าง 35 ถึง 98
    final_score = max(35, min(98, final_score))
    return int(round(final_score))


def run():
    db = SessionLocal()
    try:
        records = db.query(CallRecord).filter(CallRecord.is_active.is_(True)).all()
        print(f"พบข้อมูลทั้งหมด {len(records)} รายการ กำลังคำนวณ Agent Score ใหม่...")

        updated = 0
        for r in records:
            convo = []
            if r.conversation_json:
                try:
                    convo = json.loads(r.conversation_json) if isinstance(r.conversation_json, str) else r.conversation_json
                except Exception:
                    convo = []

            # ดึง Satisfaction score มาใช้ร่วมประเมิน
            sat_score = r.sentiment_score if (r.sentiment_score and r.sentiment_score > 5) else ((r.sentiment_score or 3) * 20)
            
            old_agent = r.agent_score
            new_agent = evaluate_agent_score(
                conversation=convo,
                action_taken=r.action_taken,
                summary=r.summary,
                sat_score=sat_score,
                anomaly_flag=r.anomaly_flag
            )
            
            r.agent_score = new_agent
            updated += 1
            print(f"ID {r.id}: Satisfaction {sat_score}/100 | Agent เดิม {old_agent} -> คำนวณใหม่ได้ {new_agent}/100")

        db.commit()
        print(f"\nอัปเดตคะแนน Agent Score สำเร็จทั้งหมด {updated} รายการ")
    except Exception as e:
        db.rollback()
        print(f"เกิดข้อผิดพลาด: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    run()