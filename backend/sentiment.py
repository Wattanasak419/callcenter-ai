# backend/sentiment.py

from transformers import pipeline

# ใช้ multilingual model
sentiment_pipeline = pipeline(
    "sentiment-analysis",
    model="nlptown/bert-base-multilingual-uncased-sentiment"
)

def analyze_sentiment(text: str):
    if not text.strip():
        return {"label": "NEUTRAL", "score": 0.0}

    result = sentiment_pipeline(text[:512])[0]

    return {
        "label": result["label"],
        "score": float(result["score"])
    }