📞 CallCenter-AI

AI-powered call analysis system for speech transcription, speaker diarization, and sentiment analysis.

🚀 Project Overview

CallCenter-AI is an AI-driven backend system designed to analyze recorded phone conversations.
The system processes audio files and automatically extracts structured insights.

✅ Core Features

🎙 Speech-to-Text Transcription (Thai supported)

👥 Speaker Diarization (Identify who spoke when)

😊 Sentiment Analysis

📊 REST API built with FastAPI

🖥 Simple frontend interface for file upload

This project is part of my AI & Cybersecurity learning journey, focusing on real-world AI integration and backend system design.

🛠 Tech Stack

Python 3.11

FastAPI

OpenAI Whisper

PyTorch

Pyannote.audio

HuggingFace Transformers

Uvicorn

📦 Installation
git clone https://github.com/wattanasak419/callcenter-ai.git
cd callcenter-ai

python -m venv venv
venv\Scripts\activate

pip install -r requirements.txt
▶️ Run the Server
uvicorn backend.main:app --host 127.0.0.1 --port 9000

Then open:

http://127.0.0.1:9000/docs
📂 Project Structure
callcenter-ai/
│
├── backend/
│   ├── main.py          # FastAPI entry point
│   ├── transcribe.py    # Whisper transcription
│   ├── diarization.py   # Speaker identification
│   ├── sentiment.py     # Sentiment analysis
│   └── database.py      # Data handling
│
├── frontend/
│   └── upload.html      # Simple UI
│
├── requirements.txt
└── README.md
⚙️ System Workflow

User uploads audio file

Backend saves file

Whisper performs transcription

Pyannote performs speaker diarization

Sentiment model analyzes tone

Structured response returned as JSON

🔥 Future Improvements

🔐 Add authentication system

🐳 Dockerize the project

☁ Deploy to cloud (AWS / GCP)

⚡ GPU acceleration

📡 Real-time streaming analysis

👨‍💻 Author

Wattanasak
Cybersecurity & AI Enthusiast
