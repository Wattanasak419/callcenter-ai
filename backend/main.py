from fastapi import FastAPI, UploadFile, File, HTTPException, Request
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.templating import Jinja2Templates

from pathlib import Path
import shutil
from fastapi.responses import FileResponse
from backend.transcribe import transcribe_audio
from backend.sentiment import analyze_sentiment
from backend.diarization import run_diarization
from . import models
from .database import engine, Base

Base.metadata.create_all(bind=engine)

# =============================
# App Configuration
# =============================
app = FastAPI(
    title="Call Center AI API",
    description="Audio Transcription + Sentiment Analysis Backend",
    version="1.0.0"
)

# File Storage
BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

# Templates
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


# =========================================================
# Utility Functions
# =========================================================
def validate_audio_file(file: UploadFile):
    """Validate uploaded file is audio"""
    if not file.content_type or not file.content_type.startswith("audio/"):
        raise HTTPException(
            status_code=400,
            detail="File must be an audio file"
        )


def save_uploaded_file(file: UploadFile) -> Path:
    """Save uploaded file to uploads directory"""
    file_path = UPLOAD_DIR / file.filename

    with file_path.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    return file_path


# =========================================================
# Routes
# =========================================================

# -----------------------------
# Root Endpoint
# -----------------------------
@app.get("/")
async def root():
    return {
        "message": "Call Center AI Backend Running 🚀",
        "docs": "/docs",
        "ui": "/ui"
    }



@app.get("/ui")
async def get_ui():
    return FileResponse("frontend/upload.html")
# -----------------------------
# Health Check
# -----------------------------
@app.get("/health")
async def health_check():
    return {"status": "ok"}


# -----------------------------
# Web UI
# -----------------------------
@app.get("/ui", response_class=HTMLResponse)
async def ui(request: Request):
    return templates.TemplateResponse(
        "index.html",
        {"request": request}
    )


# -----------------------------
# Analyze Audio API
# -----------------------------
@app.post("/analyze/", response_class=JSONResponse)
async def analyze_audio(file: UploadFile = File(...)):
    try:
        # 1️⃣ Validate file
        validate_audio_file(file)

        # 2️⃣ Save file
        file_path = save_uploaded_file(file)

        # 3️⃣ Process AI
        transcript = transcribe_audio(str(file_path))
        sentiment = analyze_sentiment(transcript)
        speakers = run_diarization(str(file_path))

        # 4️⃣ Return result
        return {
            "filename": file.filename,
            "transcript": transcript,
            "sentiment": sentiment,
            "speakers": speakers
        }

    except HTTPException as http_err:
        raise http_err

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Internal Server Error: {str(e)}"
        )