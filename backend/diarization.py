from speechbrain.inference.classifiers import EncoderClassifier
import torchaudio





# โหลดโมเดล Speaker Embedding
classifier = EncoderClassifier.from_hparams(
    source="speechbrain/spkrec-ecapa-voxceleb",
    savedir="pretrained_models/spkrec",
    local_strategy="copy"  # ป้องกันปัญหา symlink บน Windows
)


def run_diarization(audio_path: str) -> dict:
    """
    รับ path ของไฟล์เสียง
    คืนค่า embedding ของ speaker
    """

    # โหลดไฟล์เสียง
    signal, sample_rate = torchaudio.load(audio_path)

    # สร้าง embedding
    embedding = classifier.encode_batch(signal)

    # ส่งผลลัพธ์กลับ
    return {
        "status": "success",
        "sample_rate": sample_rate,
        "embedding_shape": list(embedding.shape),
    }