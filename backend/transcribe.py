import whisper

# โหลด model ครั้งเดียว
model = whisper.load_model("base")  # เปลี่ยนเป็น large ถ้าเครื่องไหว

def transcribe_audio(file_path: str):
    print(f"Transcribing file: {file_path}")
    
    result = model.transcribe(
        file_path,
        language="th",
        task="transcribe"
    )

    return result["text"]