from transformers import pipeline

def analyze_sentiment(text):
    sentiment_model = pipeline("sentiment-analysis")
    result = sentiment_model(text)[0]
    return result