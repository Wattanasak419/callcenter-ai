# backend/diarization.py
import os
import torch
import torchaudio
import numpy as np
from sklearn.cluster import AgglomerativeClustering
from speechbrain.inference.classifiers import EncoderClassifier
from speechbrain.utils.fetching import LocalStrategy  # 👈 1. Import LocalStrategy เพิ่ม

# ปิด warning และบังคับไม่ใช้ symlink
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
os.environ["HF_HUB_LOCAL_DIR_AUTO_SYMLINK_THRESHOLD"] = "0"

device = "cuda" if torch.cuda.is_available() else "cpu"

# 👈 2. ใส่ local_strategy=LocalStrategy.COPY เพื่อบังคับก๊อปปี้ไฟล์แทน symlink
classifier = EncoderClassifier.from_hparams(
    source="speechbrain/spkrec-ecapa-voxceleb",
    savedir="pretrained_models/spkrec",
    run_opts={"device": device},
    local_strategy=LocalStrategy.COPY
)

def diarize_segments(audio_path: str, segments: list) -> list:
    if not segments:
        return []

    # โหลดไฟล์เสียง
    # ถ้าเจอปัญหา backend ของ torchaudio บน Windows ให้ fallback อ่านผ่าน soundfile
    try:
        signal, fs = torchaudio.load(audio_path)
    except Exception:
        import soundfile as sf
        data, fs = sf.read(audio_path, dtype='float32')
        if len(data.shape) == 1:
            signal = torch.from_numpy(data).unsqueeze(0)
        else:
            signal = torch.from_numpy(data.T)

    # รวมช่องสัญญาณเป็น Mono หากเป็น Stereo
    if signal.shape[0] > 1:
        signal = torch.mean(signal, dim=0, keepdim=True)
        
    # แปลง Sample Rate เป็น 16,000 Hz
    if fs != 16000:
        resampler = torchaudio.transforms.Resample(fs, 16000)
        signal = resampler(signal)
        fs = 16000

    embeddings = []
    valid_indices = []

    for idx, seg in enumerate(segments):
        start_sec = seg.get("start", 0)
        end_sec = seg.get("end", 0)

        start_sample = int(start_sec * fs)
        end_sample = int(end_sec * fs)

        if end_sample <= start_sample or start_sample >= signal.shape[1]:
            continue

        chunk = signal[:, start_sample:end_sample]

        # ข้ามประโยคสั้นกว่า 0.4 วินาที
        if chunk.shape[1] < int(fs * 0.4):
            continue

        with torch.no_grad():
            emb = classifier.encode_batch(chunk.to(device))
            emb = emb.squeeze().cpu().numpy()

        embeddings.append(emb)
        valid_indices.append(idx)

    # จัดกลุ่ม Clustering 2 ผู้พูด
    if len(embeddings) >= 2:
        clustering = AgglomerativeClustering(
            n_clusters=2,
            metric="cosine",
            linkage="average"
        )
        labels = clustering.fit_predict(np.array(embeddings))

        for valid_idx, label in zip(valid_indices, labels):
            segments[valid_idx]["speaker"] = f"SPEAKER_{label:02d}"

        # เติมประโยคที่ถูกข้ามด้วย speaker ก่อนหน้า
        last_speaker = segments[valid_indices[0]]["speaker"]
        for seg in segments:
            if "speaker" not in seg:
                seg["speaker"] = last_speaker
            else:
                last_speaker = seg["speaker"]
    else:
        for seg in segments:
            seg["speaker"] = "SPEAKER_00"

    return segments