# backend/sentiment.py
from transformers import pipeline

classifier = pipeline(
    "sentiment-analysis",
    model="nlptown/bert-base-multilingual-uncased-sentiment",
    device=0  # รันบน GPU CUDA
)

def analyze_sentiment(text: str):
    """วิเคราะห์ข้อความและส่งคืนคะแนนเต็ม 100 พร้อม sentiment"""
    if not text or text.strip() == "":
        return {"score": 60, "sentiment": "neutral"}

    result = classifier(text[:512])[0]
    label = result["label"]  # เช่น "1 star", "4 stars"
    
    # สกัดตัวเลขดาว (1-5)
    stars = int(label.split()[0]) if label.split()[0].isdigit() else 3

    # แปลงระดับดาวเป็นคะแนนเต็ม 100 (1=20, 2=40, 3=60, 4=80, 5=100)
    score_100 = stars * 20

    if stars <= 2:
        sentiment = "negative"
    elif stars == 3:
        sentiment = "neutral"
    else:
        sentiment = "positive"

    return {
        "score": score_100,      # คะแนนเต็ม 100
        "stars": stars,          # จำนวนดาว 1-5
        "sentiment": sentiment   # negative / neutral / positive
    }

def calculate_satisfaction_100(customer_scores: list[int]) -> int:
    """คำนวณคะแนนเฉลี่ยความพึงพอใจของลูกค้าเต็ม 100"""
    if not customer_scores:
        return 60  # ค่ามาตรฐานระดับปานกลาง
    avg = sum(customer_scores) / len(customer_scores)
    return round(avg)