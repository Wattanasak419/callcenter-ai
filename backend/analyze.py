# backend/analyze.py
from transformers import pipeline

# เปลี่ยนกลับเป็น text-generation ตามที่ Error แนะนำ
summarizer = pipeline("text-generation", model="google/flan-t5-small") 

def summarize(text):
    if not text or len(text.strip()) < 10:
        return "ไม่มีเนื้อหาเพียงพอในการสรุป"
    try:
        # สำหรับโมเดล T5 ในโหมด text-generation ต้องใส่คำสั่งนำหน้า (Prompt)
        input_prompt = f"Summarize the following conversation: {text[:800]}"
        
        # รันผ่าน pipeline
        res = summarizer(input_prompt, max_length=100, do_sample=False)
        
        # ดึงข้อความที่เจนออกมา
        return res[0]["generated_text"]
    except Exception as e:
        print(f"Summarize Error: {e}")
        return "สรุปไม่ได้ในขณะนี้"

def analyze_by_speaker(convo_list, sentiment_model):
    """วิเคราะห์แยกพนักงานและลูกค้าจากคำหางเสียง"""
    result = []
    # คำที่บ่งบอกว่าเป็นพนักงาน
    agent_hints = ["ค่ะ", "ครับ", "สวัสดี", "ยินดีให้บริการ", "ตรวจสอบ", "เจ้าหน้าที่"]
    
    for item in convo_list:
        text = item.get("text", "")
        if not text.strip(): continue
        
        # วิเคราะห์อารมณ์
        sentiment = sentiment_model(text[:512])[0]
        
        # ตรวจสอบว่าเป็นพนักงานหรือลูกค้า
        is_agent = any(hint in text for hint in agent_hints)
        current_speaker = "พนักงาน" if is_agent else "ลูกค้า"
            
        result.append({
            "speaker": current_speaker,
            "text": text,
            "sentiment": sentiment["label"],
            "start": item.get("start", 0),
            "end": item.get("end", 0)
        })
    return result

def get_stats(conversation):
    stats = {"POSITIVE": 0, "NEGATIVE": 0}
    for c in conversation:
        label = c["sentiment"].upper()
        if any(x in label for x in ["POSITIVE", "4", "5"]):
            stats["POSITIVE"] += 1
        else:
            stats["NEGATIVE"] += 1
    return stats