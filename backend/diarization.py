import os
from pyannote.audio import Pipeline

# โหลดโมเดล
pipeline = Pipeline.from_pretrained("pyannote/speaker-diarization-3.1")

# ให้ผู้ใช้พิมพ์ชื่อไฟล์
file_name = input("Enter file name (example: audio.wav): ")

audio_file = os.path.join("backend", "uploads", file_name)

# เช็คว่าไฟล์มีอยู่จริงไหม
if not os.path.exists(audio_file):
    print("File not found!")
    exit()

print("Using file:", audio_file)

# ประมวลผล
diarization = pipeline(audio_file)

for turn, _, speaker in diarization.itertracks(yield_label=True):
    print(f"{turn.start:.1f}s - {turn.end:.1f}s : {speaker}")