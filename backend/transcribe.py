import gc
import json
import os
from pathlib import Path
import re
import threading
from faster_whisper import WhisperModel
import openai
import torch

# --- 🚀 จัดการสภาพแวดล้อม CUDA สำหรับ RTX 50-Series ---
def setup_cuda_environment():
    try:
        import nvidia.cublas
        import nvidia.cudnn

        cudnn_file = getattr(nvidia.cudnn, '__file__', None)
        cublas_file = getattr(nvidia.cublas, '__file__', None)

        valid_paths = []
        if cudnn_file:
            p = os.path.join(os.path.dirname(cudnn_file), 'bin')
            if os.path.exists(p):
                valid_paths.append(p)
                if os.name == 'nt':
                    os.add_dll_directory(p)

        if cublas_file:
            p = os.path.join(os.path.dirname(cublas_file), 'bin')
            if os.path.exists(p):
                valid_paths.append(p)
                if os.name == 'nt':
                    os.add_dll_directory(p)

        if valid_paths:
            current_path = os.environ.get('PATH') or ''
            os.environ['PATH'] = os.pathsep.join(valid_paths) + (
                os.pathsep + current_path if current_path else ''
            )
    except Exception:
        pass


setup_cuda_environment()

# --- CONFIG ---
TYPHOON_API_KEY = 'sk-kxivpnfX8MjmeW8XFGCJESTp0KA3gcoA9taum9Vs77JAk0Yf'
TYPHOON_MODEL = 'typhoon-v2.5-30b-a3b-instruct'
client = openai.OpenAI(
    api_key=TYPHOON_API_KEY,
    base_url='https://api.opentyphoon.ai/v1',
    timeout=60.0,
    max_retries=2,
)

SETTINGS_FILE = Path(__file__).resolve().parent / 'system_settings.json'
MODEL_NAMES = {
    'Faster Whisper Large v3': 'large-v3',
    'Faster Whisper Medium': 'medium',
    'Faster Whisper Small': 'small',
}

# ป้องกัน GPU แย่งคิวประมวลผลชนกัน
transcribe_lock = threading.Lock()


def get_system_settings():
    try:
        with SETTINGS_FILE.open('r', encoding='utf-8') as settings_file:
            return json.load(settings_file)
    except Exception:
        return {'speech_model': 'Auto'}


def choose_auto_model():
    if not torch.cuda.is_available():
        return 'small'
    try:
        device_properties = torch.cuda.get_device_properties(0)
        vram_gb = device_properties.total_memory / (1024**3)
        if vram_gb >= 12:
            return 'large-v3'
        if vram_gb >= 6:
            return 'medium'
    except Exception:
        pass
    return 'small'


def get_selected_model_name():
    configured_name = get_system_settings().get('speech_model', 'Auto')
    if configured_name == 'Auto':
        return choose_auto_model()
    return MODEL_NAMES.get(configured_name, 'small')


def load_whisper_model(model_name):
    print(f"กำลังโหลด Whisper {model_name}...")
    supported_compute_types = ["float16", "float32"]

    for c_type in supported_compute_types:
        try:
            print(f"ลองโหลด Whisper บน CUDA (compute_type='{c_type}')...")
            return WhisperModel(
                model_name,
                device="cuda",
                compute_type=c_type,
                download_root="./models",
            )
        except Exception as e:
            print(f"⚠️ CUDA ({c_type}) ข้ามไป: {e}")

    print("⚠️ GPU Load Failed ทั้งหมด; Fallback ไปใช้ CPU float32")
    return WhisperModel(
        model_name, device="cpu", compute_type="float32", download_root="./models"
    )


whisper_model = None
loaded_model_name = None


def get_whisper_model():
    global whisper_model, loaded_model_name
    selected_name = get_selected_model_name()
    if whisper_model is None or loaded_model_name != selected_name:
        if whisper_model is not None:
            del whisper_model
            whisper_model = None
            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        whisper_model = load_whisper_model(selected_name)
        loaded_model_name = selected_name
    return whisper_model


def clean_repeated_text(text):
    if not text:
        return ''

    # 🔥 ระบบแก้คำเฉพาะทางและชื่อแบรนด์ที่โมเดลมักถอดเพี้ยน
    brand_corrections = {
        r"ดันหลอบ": "ดันลอป",
        r"ดันหลบ": "ดันลอป",
        r"ดันลอบ": "ดันลอป",
        r"ดันหลอก": "ดันลอป",
        r"ดัลลอป": "ดันลอป",
        r"ดันล็อบ": "ดันล็อป",
        r"โอมัส": "โอมาส",
        r"โอมาซ": "โอมาส",
        r"เบดเว": "เบดเวย์",
    }
    for pattern, correct_word in brand_corrections.items():
        text = re.sub(pattern, correct_word, text, flags=re.IGNORECASE)

    # ลบคำซ้ำวนลูปผิดปกติ
    text = re.sub(r'(.{3,})(?:\s*\1){2,}', r'\1', text)
    text = re.sub(r'(.{2,})\1{3,}', r'\1', text)
    text = re.sub(
        r'(ฮาลู|อาลู|ธุท|ฮัลโหล|อ่า|เอ่อ|อืม)\s*(?:\1\s*){2,}',
        r'\1 ',
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(r'([ก-ฮะ-์a-zA-Z])\1{4,}', r'\1', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def infer_brand_from_text(text: str) -> str:
    if not text:
        return 'Unknown'
    lowered = text.lower()
    if re.search(r'\bdunlopillo\b|\bดันลอป\b|\bดันล็อป\b|\bดันหลอบ\b', lowered):
        return 'Dunlopillo'
    if re.search(r'\bomazz\b|\bโอแมซ\b|\bโอแมซซ์\b|\bออมาซ\b|\bโอมัส\b|\bโอมาส\b', lowered):
        return 'Omazz'
    if re.search(r'\blotus\b|\bโลตัส\b|\bโลตัสด\b', lowered):
        return 'Lotus'
    if re.search(r'\bbedway\b|\bเบดเวย์\b|\bเบดเวย\b', lowered):
        return 'Bedway'
    return 'Unknown'


def transcribe_audio(file_path: str):
    if not os.path.exists(file_path):
        return {'status': 'failed', 'error': 'File not found', 'conversation': []}

    with transcribe_lock:
        active_whisper_model = get_whisper_model()

        print(f'✍️ [Whisper Transcribe]: {os.path.basename(file_path)}')
        try:
            # 🔥 กำหนด initial_prompt แนะนำคลังคำศัพท์เฉพาะทางให้ Whisper
            domain_initial_prompt = (
                "บทสนทนา Call Center ฝ่ายบริการลูกค้า รับประกัน ที่นอน "
                "ดันลอป ดันล็อป Dunlopillo โอมาส โอแมซ Omazz โลตัส Lotus เบดเวย์ Bedway "
                "สวัสดีค่ะ สวัสดีครับ รบกวนถือสายสักครู่ค่ะ"
            )

            # 1. ถอดเสียงพร้อมจูน VAD และส่ง Prompt แบรนด์
            segments_gen, _ = active_whisper_model.transcribe(
                file_path,
                language='th',
                initial_prompt=domain_initial_prompt,  # 👈 ใส่ตัวชี้นำคำศัพท์
                beam_size=5,
                best_of=5,
                temperature=0.0,
                condition_on_previous_text=False,
                no_speech_threshold=0.35,
                vad_filter=True,
                vad_parameters=dict(
                    min_speech_duration_ms=100,
                    max_speech_duration_s=float('inf'),
                    min_silence_duration_ms=250,
                    speech_pad_ms=250,
                    threshold=0.35
                ),
            )

            raw_segments = []
            for s in segments_gen:
                clean_s = clean_repeated_text(s.text.strip())
                if clean_s:
                    raw_segments.append({
                        'text': clean_s,
                        'start': round(s.start, 2),
                        'end': round(s.end, 2),
                    })

            if not raw_segments:
                print(f'⚠️ ไม่พบเสียงพูด: {os.path.basename(file_path)}')
                return {
                    'status': 'failed',
                    'error': 'ไม่พบเสียงพูดในไฟล์',
                    'conversation': [],
                }

            # 2. แยก Speaker ด้วยโมเดล Diarization (ถ้ามี)
            try:
                from backend.diarization import diarize_segments
                raw_segments = diarize_segments(file_path, raw_segments)
            except Exception as d_err:
                print(f"⚠️ Diarization module bypass: {d_err}")

            # 3. จัดทำ Index และส่งข้อความให้ Typhoon LLM ช่วยระบุผู้พูด
            conversation_text_for_ai = ""
            for idx, s in enumerate(raw_segments):
                conversation_text_for_ai += f"Line {idx}: {s['text']}\n"

            role_prompt = f"""หน้าที่ของคุณคือวิเคราะห์บทสนทนา Call Center และระบุว่าแต่ละ Line ใครเป็นผู้พูด ระหว่าง 'พนักงาน' หรือ 'ลูกค้า':

แนวทางการพิจารณา:
- 'พนักงาน': พูดคำว่า ที่นอนดันลอป, โทรจาก, ขออนุญาตดูทางเจ้าหน้าที่, รบกวนคุณลูกค้าถือสาย, ติดต่อเรื่องที่นอน, นัดวัน, ให้ข้อมูลบริการ/ราคา
- 'ลูกค้า': พูดคำว่า เมื่อกี้มีสถานการณ์โทรหา, โทรมาแจ้งเรื่อง, สอบถามปัญหา, รับสาย, แป๊บหนึ่งครับ, ลืมถาม

บทสนทนา:
{conversation_text_for_ai[:3500]}

ตอบกลับเป็น JSON object เท่านั้น โดย key เป็นหมายเลข line (string) และ value เป็น 'พนักงาน' หรือ 'ลูกค้า' เช่น:
{{
  "0": "พนักงาน",
  "1": "ลูกค้า",
  "2": "ลูกค้า",
  "3": "พนักงาน"
}}
ห้ามมีคำอธิบายอื่นเด็ดขาด:"""

            roles_map = {}
            try:
                role_res = client.chat.completions.create(
                    model=TYPHOON_MODEL,
                    messages=[
                        {
                            "role": "system",
                            "content": "You are a professional dialogue classifier. Output strictly valid JSON object.",
                        },
                        {"role": "user", "content": role_prompt},
                    ],
                    temperature=0.0,
                    max_tokens=1500,
                )
                raw_roles_text = role_res.choices[0].message.content.strip()
                json_match = re.search(r'\{[\s\S]*\}', raw_roles_text)
                if json_match:
                    roles_map = json.loads(json_match.group(0))
            except Exception as llm_err:
                print(f"⚠️ Typhoon Role Mapping Error: {llm_err}")

            # 4. กำหนด Speaker ให้แต่ละ Segment พร้อม Fallback กฎคำศัพท์
            conversation_segments = []
            raw_lines = []
            current_speaker = "พนักงาน"

            for idx, s in enumerate(raw_segments):
                text_line = s['text']
                str_idx = str(idx)

                if str_idx in roles_map and roles_map[str_idx] in ["พนักงาน", "ลูกค้า"]:
                    speaker = roles_map[str_idx]
                else:
                    # Fallback rules หาก LLM ตอบไม่ครบ
                    if any(k in text_line for k in [
                        "รบกวน", "ถือสาย", "ขออนุญาตดู", "เจ้าหน้าที่", "นัดคุย", "เรียนสาย", "ยินดีให้บริการ", "ดันลอป"
                    ]):
                        speaker = "พนักงาน"
                    elif any(k in text_line for k in [
                        "เมื่อกี้มี", "โทรหา", "แป๊บหนึ่ง", "ลืมถาม", "ลูกชาย", "ได้รับสาย"
                    ]):
                        speaker = "ลูกค้า"
                    else:
                        speaker = "ลูกค้า" if current_speaker == "พนักงาน" else "พนักงาน"

                current_speaker = speaker

                conversation_segments.append({
                    'speaker': speaker,
                    'text': text_line,
                    'start': s['start'],
                    'end': s['end'],
                })
                raw_lines.append(f"{speaker}: {text_line}")

            full_text = '\n'.join(raw_lines)

            # ดักจับคำหลอนวนลูป
            if re.search(r'(\b\w+\b)(?:\s+\1){5,}', full_text) or re.search(
                r'([ก-๙a-zA-Z])\1{6,}', full_text
            ):
                print(f'⚠️ พบข้อความวนลูปหลอน: {os.path.basename(file_path)}')
                return {
                    'status': 'failed',
                    'error': 'ข้อความเสียงวนลูปหลอน',
                    'conversation': [],
                }

        except Exception as e:
            print(f'❌ Whisper Error: {e}')
            return {
                'status': 'failed',
                'error': f'Whisper Error: {str(e)}',
                'conversation': [],
            }

    # --- ขั้นตอนที่ 5: วิเคราะห์สรุปเนื้อหาและประเมินคุณภาพสายผ่าน Typhoon LLM ---
    print('🧠 ส่ง Typhoon Analysis...')
    analysis = analyze_and_split_with_typhoon(full_text)

    summary_val = (analysis.get('summary') or '').strip()

    if (
        not summary_val
        or summary_val in ['-', 'วิเคราะห์เนื้อหาเรียบร้อย']
        or 'ขัดข้อง' in summary_val
    ):
        print('❌ Typhoon สรุปเนื้อหาไม่สำเร็จ')
        return {
            'status': 'failed',
            'error': 'AI วิเคราะห์เนื้อหาไม่สำเร็จ',
            'conversation': [],
        }

    brand_value = analysis.get('brand') or infer_brand_from_text(full_text)
    brand_value = (
        brand_value.strip().title() if isinstance(brand_value, str) else 'Unknown'
    )
    if brand_value not in ('Omazz', 'Lotus', 'Bedway', 'Dunlopillo'):
        brand_value = infer_brand_from_text(full_text)

    return {
        'status': 'done',
        'filename': os.path.basename(file_path),
        'conversation': conversation_segments,
        'summary': summary_val,
        'issue': analysis.get('issue', '-'),
        'action_taken': analysis.get(
            'action_taken', 'พนักงานยังไม่ได้ระบุวิธีแก้ในสาย'
        ),
        'satisfaction_score': int(analysis.get('satisfaction_score', 3)),
        'keywords': analysis.get('keywords', ['บริการลูกค้า']),
        'anomaly_flag': analysis.get('anomaly_flag', 'no'),
        'anomaly_reason': analysis.get('anomaly_reason', ''),
        'brand': brand_value,
        'agent_performance_score': int(
            analysis.get('agent_performance_score', 3)
        ),
        'agent_performance_comment': analysis.get(
            'agent_performance_comment', ''
        ),
        'adherence': int(analysis.get('adherence', 3)),
        'politeness': int(analysis.get('politeness', 3)),
        'resolution': int(analysis.get('resolution', 3)),
        'compliance': int(analysis.get('compliance', 3)),
    }


def analyze_and_split_with_typhoon(text):
    if len(text) > 2500:
        truncated_text = text[:1500] + '\n...\n' + text[-1000:]
    else:
        truncated_text = text

    prompt = f"""คุณคือผู้เชี่ยวชาญการวิเคราะห์ Call Center จงสรุปเนื้อหาบทสนทนานี้เป็น JSON ให้ครบถ้วน:

บทสนทนา:
"{truncated_text}"

ตอบกลับเป็น JSON ตามโครงสร้างนี้เท่านั้น:
{{
  "summary": "สรุปเนื้อหาสำคัญที่พูดคุยกันอย่างชัดเจน 2-3 บรรทัด",
  "issue": "ประเด็นหลักที่ลูกค้าแจ้ง",
  "action_taken": "การดำเนินการของพนักงาน",
  "satisfaction_score": 3,
  "keywords": ["คำสำคัญ 1", "คำสำคัญ 2"],
  "brand": "Dunlopillo or Omazz or Lotus or Bedway or Unknown",
  "anomaly_flag": "no",
  "anomaly_reason": "",
  "agent_performance_score": 3,
  "agent_performance_comment": "ความคิดเห็นสั้นๆ",
  "adherence": 3,
  "politeness": 3,
  "resolution": 3,
  "compliance": 3
}}"""

    try:
        res = client.chat.completions.create(
            model=TYPHOON_MODEL,
            messages=[
                {
                    'role': 'system',
                    'content': (
                        'You are a call center auditor. Output ONLY valid JSON.'
                    ),
                },
                {'role': 'user', 'content': prompt},
            ],
            temperature=0.1,
            max_tokens=1000,
        )

        raw_content = res.choices[0].message.content.strip()
        json_match = re.search(r'\{[\s\S]*\}', raw_content)
        if json_match:
            return json.loads(json_match.group(0))

    except Exception as e:
        print(f'❌ Typhoon API Error: {e}')

    return {}