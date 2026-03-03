# =============================
# Import Libraries
# =============================
from fastapi import FastAPI, UploadFile, File, HTTPException, Request
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from diarization import run_diarization
import shutil
from pathlib import Path

from transcribe import transcribe_audio
from sentiment import analyze_sentiment


# =============================
# Initialize FastAPI App
# =============================
app = FastAPI(
    title="Call Center AI API",
    description="Audio transcription + sentiment analysis backend",
    version="1.0.0"
)

# กำหนดโฟลเดอร์เก็บไฟล์อัปโหลด
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

# กำหนดโฟลเดอร์ template สำหรับหน้าเว็บ
templates = Jinja2Templates(directory="templates")


# =============================
# Root Endpoint
# =============================
@app.get("/")
async def root():
    """
    ใช้ตรวจสอบว่า Server ทำงานอยู่
    """
    return {
        "message": "Call Center AI Backend Running 🚀",
        "docs": "/docs",
        "ui": "/ui"
    }


# =============================
# Health Check Endpoint
# =============================
@app.get("/health")
async def health_check():
    """
    ใช้สำหรับตรวจสอบสถานะระบบ (เหมาะกับ deploy)
    """
    return {"status": "ok"}


# =============================
# Web UI Endpoint
# =============================
@app.get("/ui", response_class=HTMLResponse)
async def ui(request: Request):
    """
    แสดงหน้าเว็บสำหรับอัปโหลดไฟล์เสียง
    """
    return templates.TemplateResponse("index.html", {"request": request})


# =============================
# Analyze Audio Endpoint
# =============================
@app.post("/analyze/")
async def analyze(file: UploadFile = File(...)):
    """
    รับไฟล์เสียง → ถอดเสียง → วิเคราะห์อารมณ์ → ส่งผลกลับ
    """
    try:
        # ตรวจสอบว่าเป็นไฟล์เสียง
        if not file.content_type.startswith("audio/"):
            raise HTTPException(
                status_code=400,
                detail="File must be an audio file"
            )

        # สร้าง path เก็บไฟล์
        file_path = UPLOAD_DIR / file.filename

        # บันทึกไฟล์ลงโฟลเดอร์ uploads
        with file_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # เรียกฟังก์ชันถอดเสียง
        transcript = transcribe_audio(str(file_path))

        # วิเคราะห์ sentiment
        sentiment = analyze_sentiment(transcript)

        # ส่งผลลัพธ์กลับ
        return JSONResponse(
            status_code=200,
            content={
                "filename": file.filename,
                "transcript": transcript,
                "sentiment": sentiment
            }
        )

    except HTTPException as http_err:
        raise http_err

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Internal Server Error: {str(e)}"
        )