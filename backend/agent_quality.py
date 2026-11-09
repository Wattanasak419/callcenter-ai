# backend/agent_quality.py
from typing import Dict, Any, List
import math
import json

# สัดส่วนน้ำหนักการประเมิน (ผลรวม = 1.0)
DEFAULT_WEIGHTS = {
    "adherence":  0.20,
    "politeness": 0.20,
    "resolution": 0.25,
    "compliance": 0.15,
    "sentiment":  0.20,
}


def _normalize_weights(weights: Dict[str, float]) -> Dict[str, float]:
    total = sum(weights.values())
    if total <= 0:
        return {k: 1.0 / len(weights) for k in weights}
    return {k: float(v) / total for k, v in weights.items()}


def _scale_to_100(value: Any) -> float:
    """แปลงค่า metric ใดๆ ให้กลายเป็นสเกล 0 - 100 เสมอ
    - ถ้ารับค่า <= 5.0 (สเกลเดิม 1-5) จะคูณ 20 เป็นเต็ม 100
    - ถ้ารับค่า > 5.0 (สเกลเต็ม 100 อยู่แล้ว) จะใช้ค่านั้นตรงๆ
    """
    try:
        v = float(value)
    except Exception:
        return 60.0  # ค่าเริ่มต้นระดับปานกลาง (เทียบเท่า 3/5 หรือ 60/100)

    if math.isnan(v) or math.isinf(v):
        return 60.0

    # ตรวจจับสเกล: ถ้าเป็นสเกล 0-5 ให้แปลงเป็น 0-100
    if v <= 5.0 and v > 0:
        v = v * 20.0

    return max(0.0, min(100.0, v))


def compute_agent_quality(metrics: Dict[str, Any], weights: Dict[str, float] = None) -> Dict[str, Any]:
    """คำนวณคะแนนประสิทธิภาพการทำงานของเจ้าหน้าที่ (Agent Quality Score) เต็ม 100"""
    if weights is None:
        weights = DEFAULT_WEIGHTS.copy()
    weights = _normalize_weights(weights)

    def m(k):
        v = metrics.get(k)
        if v is None:
            return 60.0
        return _scale_to_100(v)

    parts_100 = {
        "adherence":  m("adherence"),
        "politeness": m("politeness"),
        "resolution": m("resolution"),
        "compliance": m("compliance"),
        "sentiment":  m("sentiment"),
    }

    breakdown = {}
    total_score_100 = 0.0

    for k, w in weights.items():
        val = parts_100.get(k, 60.0)
        contribution = val * w
        breakdown[k] = {
            "value_100": round(val, 2),
            "value_5": round(val / 20.0, 2),
            "weight": round(w, 3),
            "contribution": round(contribution, 2),
        }
        total_score_100 += contribution

    score_100 = round(total_score_100, 2)
    score_5   = round(total_score_100 / 20.0, 2)

    return {
        "score_100": score_100,  # คะแนนหลักเต็ม 100
        "score_5":   score_5,    # คะแนนเทียบเคียงเต็ม 5
        "breakdown": breakdown,
        "raw_parts": parts_100,
    }


def evaluate_conversation(conversation: List[Dict[str, Any]]) -> Dict[str, Any]:
    """คำนวณสัดส่วนคำพูดของพนักงานและลูกค้า"""
    agent_words = customer_words = 0
    for turn in conversation:
        speaker = (turn.get("speaker") or "").lower()
        text = turn.get("text") or ""
        words = turn.get("words") or len(text.split())
        if "agent" in speaker or "พนักงาน" in speaker:
            agent_words += int(words)
        else:
            customer_words += int(words)
            
    total = agent_words + customer_words
    return {
        "agent_words":    agent_words,
        "customer_words": customer_words,
        "agent_ratio":    round(agent_words / total, 3) if total else 0.5,
    }


if __name__ == "__main__":
    # ตัวอย่างทดสอบ: รองรับทั้งค่าที่ส่งมาเป็นสเกล 1-5 หรือเต็ม 100
    sample = {
        "adherence":  4.0,   # สเกลเดิม -> จะถูกแปลงเป็น 80
        "politeness": 4.5,   # สเกลเดิม -> จะถูกแปลงเป็น 90
        "resolution": 60.0,  # สเกลเต็ม 100 อยู่แล้ว
        "sentiment":  80.0,  # สเกลเต็ม 100 อยู่แล้ว
        "compliance": 3.5,   # สเกลเดิม -> จะถูกแปลงเป็น 70
    }
    print(json.dumps(compute_agent_quality(sample), ensure_ascii=False, indent=2))