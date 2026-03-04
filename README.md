# 📞 CallCenter-AI

AI-powered call analysis system for speech transcription, speaker diarization, and sentiment analysis.

---

## 🚀 Project Overview

CallCenter-AI is a backend system that processes call recordings and provides:

- 🎙 Speech-to-Text Transcription
- 👥 Speaker Diarization (Who spoke when)
- 😊 Sentiment Analysis
- 📊 Backend API built with FastAPI

This project is built as part of my AI & Cybersecurity learning journey.

---

## 🛠 Tech Stack

- Python 3.11
- FastAPI
- PyTorch
- Pyannote.audio
- Transformers
- Uvicorn

---

## 📦 Installation

```bash
git clone https://github.com/wattanasak419/callcenter-ai.git
cd callcenter-ai
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

---

## ▶️ Run the Server

```bash
uvicorn backend.main:app --reload
```

Open browser:
```
http://127.0.0.1:8000/docs
```

---

## 📂 Project Structure

```
callcenter-ai/
│
├── backend/
│   ├── main.py
│   ├── transcribe.py
│   ├── diarization.py
│   ├── sentiment.py
│   └── database.py
│
├── frontend/
│   └── upload.html
│
├── pretrained_models/
└── README.md
```

---

## 🔥 Future Improvements

- Add authentication system
- Dockerize the project
- Deploy to cloud
- Improve model performance
- Add real-time call processing

---

## 👨‍💻 Author

Wattanasak  
Cybersecurity & AI Enthusiast
