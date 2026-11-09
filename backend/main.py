"""Enterprise Queue System & CallCenter AI Entrypoint.

Integrated with Safe Thread-Safe Background Task Queue to prevent
CUDA OOM, GPU concurrency conflicts, and SQLAlchemy QueuePool Timeout errors.
"""
from contextlib import asynccontextmanager
import calendar
import csv
from datetime import date, datetime, timedelta
import gc
import hashlib
import hmac
import io
import json
import os
from pathlib import Path
import re
import shutil
import threading

from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import (
    FileResponse,
    HTMLResponse,
    JSONResponse,
    RedirectResponse,
    StreamingResponse,
)
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import requests
from sqlalchemy import func, inspect, text
from sqlalchemy.orm import Session
import torch

from backend.database import SessionLocal, engine
from backend.models import Agent, CallRecord

# 🛠️ Fix torchaudio backend compatibility for SpeechBrain
import torchaudio
if not hasattr(torchaudio, "list_audio_backends"):
    torchaudio.list_audio_backends = lambda: ["soundfile"]

# 🔥 Import โมดูล Diarization และ Analyze
try:
    from backend.diarization import diarize_segments
except ImportError:
    try:
        from diarization import diarize_segments
    except ImportError:
        diarize_segments = None

try:
    from backend.analyze import analyze_by_speaker
except ImportError:
    try:
        from analyze import analyze_by_speaker
    except ImportError:
        analyze_by_speaker = None

# 🤖 Import Discord Bot Service
try:
    from backend.discord_bot_service import (
        run_discord_bot_background,
        send_interactive_case_alert,
        trigger_discord_claim_notification,
        bot,
    )
except ImportError:
    try:
        from discord_bot_service import (
            run_discord_bot_background,
            send_interactive_case_alert,
            trigger_discord_claim_notification,
            bot,
        )
    except ImportError:
        run_discord_bot_background = None
        send_interactive_case_alert = None
        trigger_discord_claim_notification = None
        bot = None

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(BASE_DIR, ".."))

# 📂 ค้นหา uploads และ templates ตามโครงสร้างจริง
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

possible_templates = [
    os.path.join(BASE_DIR, "templates"),
    os.path.join(PROJECT_ROOT, "templates"),
]
TEMPLATES_DIR = next((d for d in possible_templates if os.path.exists(d)), possible_templates[0])

# Auth Configurations
AUTH_COOKIE = "callcenter_auth"
AUTH_SECRET = os.getenv("CALLCENTER_SECRET_KEY", "callcenter_jwt_secret_dev_key_2026")


# ==========================================
# 🗄️ Database Session Dependency
# ==========================================
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _make_auth_token(agent_code: str) -> str:
    sig = hmac.new(AUTH_SECRET.encode(), agent_code.encode(), hashlib.sha256).hexdigest()
    return f"{agent_code}.{sig}"


def load_system_settings() -> dict:
    settings_path = os.path.join(BASE_DIR, "system_settings.json")
    if os.path.exists(settings_path):
        try:
            with open(settings_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"session_timeout": 8}


def normalize_keywords(keywords_val) -> list[str]:
    if not keywords_val:
        return []
    if isinstance(keywords_val, list):
        return [str(k).strip() for k in keywords_val if str(k).strip()]
    if isinstance(keywords_val, str):
        try:
            parsed = json.loads(keywords_val)
            if isinstance(parsed, list):
                return [str(k).strip() for k in parsed if str(k).strip()]
        except Exception:
            pass
        return [k.strip() for k in keywords_val.split(",") if k.strip()]
    return []


def normalize_phone_number(phone_str: str | None) -> str:
    if not phone_str:
        return ""
    digits = re.sub(r"\D", "", str(phone_str))
    if digits.startswith("66") and len(digits) == 11:
        return "0" + digits[2:]
    return digits


# ==========================================
# 🔍 ฟังก์ชันดักจับแบรนด์ (Lotus / Omazz)
# ==========================================
def detect_brand_from_text(text_content: str, fallback_brand: str = "Unknown") -> str:
    if not text_content:
        return fallback_brand if fallback_brand != "Unknown" else "Unknown"

    text_lower = text_content.lower()
    if re.search(r"(omazz|โอมาส|โอมัส|โอมาซ)", text_lower):
        return "Omazz"
    if re.search(r"(lotus|โลตัส)", text_lower):
        return "Lotus"
    return fallback_brand if fallback_brand else "Unknown"


# ==========================================
# 🚀 THREAD-SAFE REORDERABLE QUEUE SYSTEM
# ==========================================
class ReorderableAudioQueue:
    def __init__(self):
        self._queue = []
        self._current_task = None
        self._lock = threading.Lock()
        self._has_item_event = threading.Event()

    def put(self, file_path: str, record_id: int, filename: str):
        with self._lock:
            self._queue.append({
                "record_id": record_id,
                "file_path": file_path,
                "filename": filename,
                "created_at": datetime.now().strftime("%H:%M:%S"),
            })
            self._has_item_event.set()

    def get_next(self):
        while True:
            self._has_item_event.wait()
            with self._lock:
                if self._queue:
                    self._current_task = self._queue.pop(0)
                    if not self._queue:
                        self._has_item_event.clear()
                    return self._current_task
                else:
                    self._has_item_event.clear()

    def clear_current(self):
        with self._lock:
            self._current_task = None

    def move_item(self, record_id: int, direction: str) -> bool:
        with self._lock:
            idx = next(
                (i for i, item in enumerate(self._queue) if item["record_id"] == record_id),
                None,
            )
            if idx is None:
                return False
            if direction == "up" and idx > 0:
                self._queue[idx], self._queue[idx - 1] = (
                    self._queue[idx - 1],
                    self._queue[idx],
                )
                return True
            elif direction == "down" and idx < len(self._queue) - 1:
                self._queue[idx], self._queue[idx + 1] = (
                    self._queue[idx + 1],
                    self._queue[idx],
                )
                return True
            return False

    def list_status(self):
        with self._lock:
            return {
                "current_processing": self._current_task,
                "waiting_queue": list(self._queue),
                "total_waiting": len(self._queue),
            }


audio_task_queue = ReorderableAudioQueue()


def background_audio_worker():
    """Background Worker ดึงไฟล์จากคิวมาประมวลผลทีละไฟล์ (Sequential Processing)"""
    print("🚀 [Queue Worker] ระบบประมวลผลคิวเสียงเริ่มต้นทำงานแล้ว...")
    while True:
        task = audio_task_queue.get_next()
        if not task:
            continue

        file_path = task["file_path"]
        record_id = task["record_id"]

        print(f"📥 [Worker] กำลังประมวลผลไฟล์ ID: {record_id} ({os.path.basename(file_path)})")

        db = SessionLocal()
        try:
            record = db.query(CallRecord).filter(CallRecord.id == record_id).first()
            if not record:
                continue

            record.status = "processing"
            db.commit()

            try:
                from backend.transcribe import transcribe_audio
                analysis_result = transcribe_audio(file_path)
            except Exception:
                analysis_result = {"conversation": [], "summary": "ไม่สามารถประมวลผลได้"}

            raw_conv = analysis_result.get("conversation", [])

            if isinstance(raw_conv, list) and len(raw_conv) > 0 and diarize_segments and analyze_by_speaker:
                try:
                    diarized_conv = diarize_segments(file_path, raw_conv)
                    sentiment_model = None
                    try:
                        from transformers import pipeline
                        sentiment_model = pipeline(
                            "sentiment-analysis",
                            model="airesearch/wangchanberta-base-att-spm-ontonotes5",
                        )
                    except Exception:
                        pass

                    formatted_conv = analyze_by_speaker(diarized_conv, sentiment_model)
                    analysis_result["conversation"] = formatted_conv
                except Exception as diarize_err:
                    print(f"⚠️ [Worker Diarization Warning]: {diarize_err} ใช้ผล fallback")

            record = db.query(CallRecord).filter(CallRecord.id == record_id).first()
            if record:
                conv = analysis_result.get("conversation", [])
                summary_val = (analysis_result.get("summary") or "").strip()
                has_conversation = bool(isinstance(conv, list) and len(conv) > 0)

                if has_conversation:
                    full_conv_text = " ".join([
                        item.get("text", "")
                        for item in conv
                        if isinstance(item, dict) and item.get("text")
                    ])
                    detected_brand = detect_brand_from_text(
                        full_conv_text,
                        fallback_brand=analysis_result.get("brand", "Unknown"),
                    )

                    raw_score = analysis_result.get("satisfaction_score", 60)
                    if raw_score is not None:
                        try:
                            val = float(raw_score)
                            final_score = int(round(val * 20)) if val <= 5 else int(round(val))
                        except (ValueError, TypeError):
                            final_score = 60
                    else:
                        final_score = 60

                    record.status = "done"
                    record.summary = summary_val if summary_val else "บันทึกบทสนทนาเรียบร้อย"
                    record.issue = analysis_result.get("issue", "-")
                    record.action_taken = analysis_result.get("action_taken", "-")
                    record.sentiment_score = final_score
                    record.brand = detected_brand
                    record.agent_score = analysis_result.get("agent_performance_score", 3)
                    record.agent_comment = analysis_result.get("agent_performance_comment", "")
                    record.adherence = analysis_result.get("adherence", 3)
                    record.politeness = analysis_result.get("politeness", 3)
                    record.resolution = analysis_result.get("resolution", 3)
                    record.compliance = analysis_result.get("compliance", 3)
                    record.conversation_json = json.dumps(conv, ensure_ascii=False)
                    record.is_active = True
                    db.commit()
                    print(f"✅ [Worker] บันทึกผลสำเร็จ Record ID: {record_id} [Brand: {detected_brand}] [Score: {final_score}/100]")
                else:
                    db.delete(record)
                    db.commit()
                    if os.path.exists(file_path):
                        try:
                            os.remove(file_path)
                        except OSError:
                            pass

        except Exception as e:
            print(f"❌ [Worker Error] คิวไฟล์ ID {record_id} ล้มเหลว: {str(e)}")
            try:
                record = db.query(CallRecord).filter(CallRecord.id == record_id).first()
                if record:
                    db.delete(record)
                    db.commit()
                if os.path.exists(file_path):
                    try:
                        os.remove(file_path)
                    except OSError:
                        pass
            except Exception as cleanup_err:
                db.rollback()
                print(f"⚠️ [Worker Cleanup Error]: {cleanup_err}")
        finally:
            db.close()
            audio_task_queue.clear_current()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            gc.collect()


# ==========================================
# 🧹 SCHEMA MIGRATION & LIFESPAN
# ==========================================
def _migrate_review_schema() -> None:
    inspector = inspect(engine)
    if inspector.has_table("call_records"):
        cols = {c["name"] for c in inspector.get_columns("call_records")}
        with engine.begin() as conn:
            if "is_active" not in cols:
                conn.execute(
                    text("ALTER TABLE call_records ADD COLUMN is_active BOOLEAN DEFAULT 1")
                )
            conn.execute(
                text("UPDATE call_records SET is_active=0 WHERE status IN ('deleted','pending_delete','disabled')")
            )
            conn.execute(
                text("UPDATE call_records SET is_active=1 WHERE is_active IS NULL")
            )
    if inspector.has_table("agents"):
        cols = {c["name"] for c in inspector.get_columns("agents")}
        with engine.begin() as conn:
            if "is_active" not in cols:
                conn.execute(
                    text("ALTER TABLE agents ADD COLUMN is_active BOOLEAN DEFAULT 1")
                )
            conn.execute(
                text("UPDATE agents SET is_active=1 WHERE is_active IS NULL")
            )


_migrate_review_schema()


@asynccontextmanager
async def lifespan(app: FastAPI):
    worker_thread = threading.Thread(target=background_audio_worker, daemon=True)
    worker_thread.start()

    bot_token = os.getenv("DISCORD_BOT_TOKEN")
    if bot_token and run_discord_bot_background:
        try:
            run_discord_bot_background(bot_token)
        except Exception as e:
            print(f"⚠️ [Discord Bot Startup Warning]: {e}")

    db = SessionLocal()
    try:
        stale_records = (
            db.query(CallRecord)
            .filter(CallRecord.status.in_(["processing", "failed"]))
            .all()
        )
        for rec in stale_records:
            if rec.filename:
                stale_file = os.path.join(UPLOAD_DIR, rec.filename)
                if os.path.exists(stale_file):
                    try:
                        os.remove(stale_file)
                    except OSError:
                        pass
            db.delete(rec)
        db.commit()

        pending_records = (
            db.query(CallRecord).filter(CallRecord.status == "pending").all()
        )
        for precord in pending_records:
            pfile_path = os.path.join(UPLOAD_DIR, precord.filename)
            if os.path.exists(pfile_path):
                audio_task_queue.put(
                    file_path=pfile_path,
                    record_id=precord.id,
                    filename=precord.filename,
                )
    except Exception as e:
        db.rollback()
        print(f"⚠️ [Startup Pipeline Error]: {e}")
    finally:
        db.close()

    yield


app = FastAPI(title="OMAZZ CALLING API", lifespan=lifespan)

# Mount static & uploads
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")


# ==========================================
# 🔐 AUTH & RBAC MATRIX แยกตามตำแหน่ง
# ==========================================
PERMISSIONS_CONFIG = [
    {"key": "view_dashboard", "category": "ระบบงานหลัก", "label": "เข้าถึงแดชบอร์ด (Dashboard)", "staff": True, "supervisor": True, "it": False},
    {"key": "view_customers", "category": "ระบบงานหลัก", "label": "ดูข้อมูลลูกค้า (Customers)", "staff": True, "supervisor": True, "it": False},
    {"key": "register_customer", "category": "ระบบงานหลัก", "label": "ลงทะเบียนลูกค้าใหม่ (Register)", "staff": True, "supervisor": True, "it": False},
    {"key": "upload_audio", "category": "ระบบงานหลัก", "label": "อัปโหลดและประมวลผลเสียง (Upload)", "staff": True, "supervisor": True, "it": False},
    {"key": "transfer_cases", "category": "การจัดการเคส", "label": "ส่งต่อเคสสนทนา (Transfer Case)", "staff": True, "supervisor": True, "it": False},
    {"key": "manage_record_status", "category": "การจัดการเคส", "label": "เปิด/ปิดสถานะเคส (Enable/Disable)", "staff": True, "supervisor": True, "it": True},
    {"key": "view_agents", "category": "ผู้ดูแลระบบ", "label": "ดูรายชื่อพนักงาน (Employees)", "staff": False, "supervisor": True, "it": True},
    {"key": "manage_agents", "category": "ผู้ดูแลระบบ", "label": "จัดการข้อมูลพนักงาน (Add/Edit Agents)", "staff": False, "supervisor": False, "it": True},
    {"key": "view_permissions", "category": "ผู้ดูแลระบบ", "label": "จัดการสิทธิ์และตั้งค่า (Matrix & Settings)", "staff": False, "supervisor": False, "it": True},
]


def load_permissions_matrix() -> list[dict]:
    matrix_file = os.path.join(BASE_DIR, "permission_matrix.json")
    if os.path.exists(matrix_file):
        try:
            with open(matrix_file, "r", encoding="utf-8") as f:
                saved = json.load(f)
                if isinstance(saved, dict) and "permissions" in saved:
                    return saved["permissions"]
                elif isinstance(saved, list):
                    return saved
        except Exception:
            pass
    return PERMISSIONS_CONFIG


def _permission_matrix() -> list[dict]:
    return load_permissions_matrix()


def _has_permission(agent: Agent, key: str) -> bool:
    role = (agent.role or "staff").strip().lower()
    item = next((p for p in _permission_matrix() if p["key"] == key), None)
    return bool(item and item.get(role, False))


def _auth_agent(request: Request, db: Session) -> Agent | None:
    token = request.cookies.get(AUTH_COOKIE, "")
    agent_code, sep, signature = token.rpartition(".")
    if not sep:
        return None
    expected = hmac.new(AUTH_SECRET.encode(), agent_code.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(signature, expected):
        return None
    agent = db.query(Agent).filter(Agent.agent_code == agent_code).first()
    if not agent or not bool(agent.is_active):
        return None
    return agent


def _required_permission(path: str, method: str) -> str | None:
    if path in {"/dashboard", "/stats", "/files"}:
        return "view_dashboard"
    if path in {"/add-customer", "/add_customer", "/api/manual_add"}:
        return "register_customer"
    if path == "/upload" or path.startswith("/api/queue"):
        return "upload_audio"
    if path in {"/employees", "/permissions"}:
        return "view_agents"
    if path.startswith(("/permission-matrix", "/permission_matrix", "/system-settings", "/system_settings")):
        return "view_permissions"
    if path.startswith(("/api/agents", "/api/employees")):
        return "view_agents" if method == "GET" else "manage_agents"
    if path.startswith("/api/cases/") and path.endswith("/status"):
        return None  # ปลดล็อกให้สลับเปิด/ปิดสถานะได้
    if path.startswith(("/api/cases/", "/api/transfer-targets")) and path.endswith("/transfer"):
        return "transfer_cases"
    if path.startswith(("/customers", "/warranty", "/api/customers", "/api/history/", "/status/", "/download/", "/export/")):
        return "view_customers"
    return None


@app.middleware("http")
async def enforce_active_account_and_rbac(request: Request, call_next):
    path = request.url.path

    public_paths = {
        "/", "/api/login", "/api/logout", "/healthz", "/readyz",
        "/openapi.json", "/docs", "/redoc", "/api/cases/send-discord-direct"
    }
    if path in public_paths or path.startswith(("/docs/", "/uploads/", "/static/")):
        return await call_next(request)

    db = SessionLocal()
    agent = None
    try:
        agent = _auth_agent(request, db)
    finally:
        db.close()

    if not agent:
        if path.startswith("/api/") or path.startswith(("/stats", "/files", "/status/", "/download/", "/export/")):
            return JSONResponse(status_code=401, content={"detail": "กรุณาเข้าสู่ระบบ"})
        return RedirectResponse(url="/", status_code=303)

    permission = _required_permission(path, request.method.upper())
    if permission and not _has_permission(agent, permission):
        role = (agent.role or "staff").lower()
        if path == "/dashboard" and role == "it":
            return RedirectResponse(url="/employees", status_code=303)
        if role == "staff" and path in {"/employees", "/permission-matrix", "/system-settings"}:
            return RedirectResponse(url="/dashboard", status_code=303)

        if path.startswith("/api/") or path.startswith(("/stats", "/files", "/status/", "/download/", "/export/")):
            return JSONResponse(status_code=403, content={"detail": "ตำแหน่งของคุณไม่มีสิทธิ์ใช้งานส่วนนี้"})
        return RedirectResponse(url="/employees" if role == "it" else "/dashboard", status_code=303)

    return await call_next(request)


def _render_template(filename: str) -> HTMLResponse:
    file_path = os.path.join(TEMPLATES_DIR, filename)
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    raise HTTPException(status_code=404, detail=f"ไม่พบไฟล์เทมเพลต: {filename}")


def _parse_date(value: str | None) -> date | None:
    if not value or value == "-":
        return None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(value.strip(), fmt).date()
        except (ValueError, AttributeError):
            pass
    return None


def _add_months(base: date, months: int) -> date:
    idx = base.month - 1 + months
    year, month = base.year + idx // 12, idx % 12 + 1
    return date(year, month, min(base.day, calendar.monthrange(year, month)[1]))


def _warranty_end(record: CallRecord) -> str | None:
    explicit = _parse_date(record.end_date)
    if explicit:
        return explicit.isoformat()
    start = _parse_date(record.purchase_date) or _parse_date(record.start_date)
    duration = (record.warranty_duration or "").strip().lower()
    if not start or not duration:
        return None
    match = re.search(r"(\d+(?:\.\d+)?)", duration)
    if not match:
        return None
    amount = float(match.group(1))
    if "month" in duration or "เดือน" in duration:
        return _add_months(start, int(round(amount))).isoformat()
    if "year" in duration or "yr" in duration or "ปี" in duration:
        return _add_months(start, int(round(amount * 12))).isoformat()
    if "day" in duration or "วัน" in duration:
        return (start + timedelta(days=int(round(amount)))).isoformat()
    return None


def record_to_dict(record: CallRecord):
    if not record:
        return None
    keywords = normalize_keywords(record.keywords)
    active = bool(record.is_active)

    actual_status = record.status or "pending"
    warranty_end = _warranty_end(record)
    warranty_status = "unknown"
    if warranty_end:
        parsed = _parse_date(warranty_end)
        if parsed:
            warranty_status = "active" if parsed >= date.today() else "expired"

    agent_info = None
    if record.agent:
        agent_info = {
            "agent_code": record.agent.agent_code,
            "firstname": record.agent.firstname,
            "lastname": record.agent.lastname,
            "nickname": record.agent.nickname,
            "role": record.agent.role,
            "department": record.agent.department,
            "position": record.agent.position,
            "phone": record.agent.phone,
            "email": record.agent.email,
            "is_active": bool(record.agent.is_active),
        }

    return {
        "id": record.id,
        "filename": record.filename,
        "firstname": record.firstname,
        "lastname": record.lastname,
        "age": record.age,
        "customer_phone": record.customer_phone,
        "brand": record.brand,
        "warranty_number": record.warranty_number or f"WR-{record.id:06d}",
        "product_name": record.product_name,
        "serial_number": record.serial_number,
        "purchase_date": record.purchase_date,
        "warranty_duration": record.warranty_duration,
        "warranty_terms": record.warranty_terms,
        "warranty_end_date": warranty_end,
        "warranty_status": warranty_status,
        "direction": record.direction,
        "address": record.address,
        "start_date": record.start_date,
        "end_date": record.end_date,
        "policy_expiry_list": [warranty_end] if warranty_end else [],
        "call_count": record.call_count,
        "action_taken": record.action_taken,
        "keywords": keywords,
        "anomaly_flag": record.anomaly_flag,
        "anomaly_reason": record.anomaly_reason,
        "agent_score": record.agent_score,
        "agent_comment": record.agent_comment,
        "agent_performance_comment": record.agent_comment,
        "adherence": record.adherence,
        "politeness": record.politeness,
        "resolution": record.resolution,
        "compliance": record.compliance,
        "issue": record.issue,
        "summary": record.summary,
        "sentiment_score": record.sentiment_score,
        "conversation_json": record.conversation_json,
        "status": actual_status if active else "disabled",
        "processing_status": actual_status,
        "is_active": active,
        "file_hash": record.file_hash,
        "created_at": (
            record.created_at.isoformat() if record.created_at else None
        ),
        "agent_code": record.agent_code,
        "assigned_agent_code": record.assigned_agent_code,
        "agent": agent_info,
    }


# ==========================================
# 📋 SCHEMAS
# ==========================================
class RoleUpdate(BaseModel):
    role: str

class AgentStatusUpdate(BaseModel):
    enabled: bool

class AgentCreate(BaseModel):
    agent_code: str
    password: str
    firstname: str
    lastname: str
    nickname: str | None = None
    age: int | None = None
    gender: str | None = None
    address: str | None = None
    phone: str | None = None
    email: str | None = None
    emergency_contact: str | None = None
    department: str | None = None
    position: str | None = None
    start_work_date: str | None = None
    role: str = "staff"

class CaseTransfer(BaseModel):
    assigned_agent_code: str

class QueueReorder(BaseModel):
    record_id: int
    direction: str


# ==========================================
# 🌐 HTML PAGES ROUTING
# ==========================================
@app.get("/", response_class=HTMLResponse)
def index_page():
    return _render_template("index.html")


@app.get("/dashboard", response_class=HTMLResponse)
def dashboard_page():
    return _render_template("dashboard.html")


@app.get("/customers", response_class=HTMLResponse)
def customers_page():
    return _render_template("customers.html")


@app.get("/upload", response_class=HTMLResponse)
def upload_page():
    return _render_template("upload.html")


@app.get("/warranty", response_class=HTMLResponse)
def warranty_default_page():
    return _render_template("warranty.html")


# 🛠️ Warranty Page Renderer: แทนที่ค่าตัวแปรลงใน HTML โดยตรง
@app.get("/warranty/{item_id}", response_class=HTMLResponse)
def get_warranty_page(item_id: int, db: Session = Depends(get_db)):
    rec = db.query(CallRecord).filter(CallRecord.id == item_id).first()
    if not rec:
        raise HTTPException(status_code=404, detail="ไม่พบข้อมูลการรับประกัน")

    file_path = os.path.join(TEMPLATES_DIR, "warranty.html")
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="ไม่พบไฟล์เทมเพลต warranty.html")

    with open(file_path, "r", encoding="utf-8") as f:
        html_content = f.read()

    # --- 1. คลังชื่อ 20 ชื่อ, นามสกุล 20 นามสกุล และเบอร์โทร 20 เบอร์ สำหรับสุ่มเมื่อไม่มีข้อมูล ---
    firstnames_pool = [
        "กิตติศักดิ์", "วิภาดา", "ธนพล", "นภัสสร", "ศิริพร",
        "ชลธิชา", "ปิยะพงษ์", "อัญชลี", "วรวุฒิ", "กานดา",
        "ณัฐวุฒิ", "พัชราภา", "สุทธิพงษ์", "รัตนพร", "ธีรภัทร",
        "มณีรัตน์", "ชยานันต์", "เบญจมาศ", "ภานุพงศ์", "อรวรรณ"
    ]
    lastnames_pool = [
        "สมโลก", "รัตนโชติ", "เจริญสุข", "วงศ์สวัสดิ์", "สุขเจริญ",
        "ศรีสุข", "บูรณพงศ์", "พิทักษ์ธรรม", "จันทรา", "ตั้งเจริญ",
        "วัฒนพานิช", "รุ่งเรือง", "ประสิทธิ์โชค", "มงคลสวัสดิ์", "เลิศวิจิตร",
        "สุวรรณโรจน์", "เกียรติไพบูลย์", "ทรัพย์เจริญ", "ทวีวัฒนา", "ชินบุตร"
    ]
    phones_pool = [
        "0812345678", "0823456789", "0834567890", "0845678901", "0856789012",
        "0867890123", "0878901234", "0889012345", "0890123456", "0801234567",
        "0912345678", "0923456789", "0934567890", "0945678901", "0956789012",
        "0967890123", "0978901234", "0989012345", "0990123456", "0901234567"
    ]

    # --- ตรวจสอบชื่อลูกค้า ---
    fname = getattr(rec, "firstname", None)
    lname = getattr(rec, "lastname", None)
    cust_name = getattr(rec, "customer_name", None)

    if not fname or str(fname).strip() in ["-", "", "None", "Unknown"]:
        if cust_name and str(cust_name).strip() not in ["-", "", "None", "Unknown"]:
            parts = cust_name.strip().split(maxsplit=1)
            fname = parts[0]
            lname = parts[1] if len(parts) > 1 else ""
        else:
            fname = firstnames_pool[rec.id % len(firstnames_pool)]
            lname = lastnames_pool[(rec.id * 3) % len(lastnames_pool)]

    if not lname or str(lname).strip() in ["-", "", "None"]:
        lname = lastnames_pool[(rec.id * 2) % len(lastnames_pool)]

    # --- ตรวจสอบเบอร์โทรศัพท์ ---
    phone = (getattr(rec, "customer_phone", "") or "").replace("-", "").strip()
    if not phone or phone in ["-", "", "None", "Unknown"]:
        phone = phones_pool[rec.id % len(phones_pool)]
        
    # --- 2. ค้นหาประวัติสายและแบรนด์ ---
    phone = (rec.customer_phone or "").replace("-", "").strip()
    history = []
    if phone:
        history = db.query(CallRecord).filter(CallRecord.customer_phone.like(f"%{phone}%")).all()
    
    total_calls = len(history) if history else 1

    all_text = ""
    for r in (history if history else [rec]):
        all_text += f" {getattr(r, 'summary', '')} {getattr(r, 'issue_topic', '')} {getattr(r, 'action_taken', '')}"

    detected_brand = rec.brand
    if history:
        for h in history:
            b = getattr(h, "brand", "")
            if b and str(b).strip() not in ["Unknown", "-", "", "None"]:
                detected_brand = b
                break

    if not detected_brand or str(detected_brand).strip() in ["Unknown", "-", "", "None"]:
        if "โลตัส" in all_text or "Lotus" in all_text:
            detected_brand = "Lotus"
        elif "โอมาซ" in all_text or "Omazz" in all_text:
            detected_brand = "Omazz"
        else:
            detected_brand = "Lotus" if (rec.id % 2 == 0) else "Omazz"

    # --- 3. คลังสินค้า / รุ่นสำหรับสุ่มแยกตามแบรนด์ ---
    omazz_models = [
        "Fairmont",
        "Grand Frank Monte",
        "Falcohn",
        "Frank Monte",
        "Earth Eco",
        "Fanthom"
    ]
    lotus_models = [
        "Royal California",
        "O-Season I",
        "Stella",
        "Nature Touch",
        "Marshall Deluxe",
        "Euphoria"
    ]

    product_name_val = getattr(rec, "product_name", None)
    if not product_name_val or str(product_name_val).strip() in ["-", "", "None", "ที่นอนสปริง Omazz", "ที่นอนสปริง Lotus", "ที่นอน Lotus (มาตรฐาน)"]:
        if str(detected_brand).lower() == "omazz":
            product_name_val = omazz_models[rec.id % len(omazz_models)]
        else:
            product_name_val = lotus_models[rec.id % len(lotus_models)]

    # --- 4. วันที่และระยะเวลารับประกัน ---
    w_start = getattr(rec, "start_date", None) or getattr(rec, "purchase_date", None) or "2022-12-01"
    w_end = _warranty_end(rec) or getattr(rec, "warranty_end_date", None) or getattr(rec, "end_date", None) or "2032-12-01"
    purchase_date_val = getattr(rec, "purchase_date", None) or w_start

    duration_val = getattr(rec, "warranty_duration", None)
    if not duration_val or str(duration_val).strip() in ["-", "", "None"]:
        try:
            s_yr = int(str(w_start)[:4])
            e_yr = int(str(w_end)[:4])
            diff = e_yr - s_yr
            duration_val = f"{diff} ปี" if diff > 0 else "10 ปี"
        except Exception:
            duration_val = "10 ปี"

    # --- 5. Serial Number และ ผู้รับผิดชอบเคส ---
    serial_val = getattr(rec, "serial_number", None)
    if not serial_val or str(serial_val).strip() in ["-", "", "None"]:
        last_digits = phone[-4:] if len(phone) >= 4 else f"{rec.id:04d}"
        serial_val = f"SN-{rec.id:04d}-{last_digits}"

    agent_val = getattr(rec, "assigned_agent_code", None) or getattr(rec, "agent_code", None)
    if not agent_val or str(agent_val).strip() in ["-", "", "None"]:
        agents_pool = ["AGT-101", "AGT-102", "AGT-201", "AGT-204", "EMP001", "EMP003"]
        agent_val = agents_pool[rec.id % len(agents_pool)]

    # --- 6. สถานะและเงื่อนไข ---
    w_status = "active"
    status_badge = "อยู่ในประกัน"
    if w_end and w_end != "-":
        parsed = _parse_date(w_end)
        if parsed and parsed < date.today():
            w_status = "expired"
            status_badge = "หมดประกัน"

    w_number = getattr(rec, "warranty_number", None) or f"WR-{rec.id:06d}"
    disabled_notice = ""
    if not bool(getattr(rec, "is_active", True)) or getattr(rec, "status", None) == "disabled":
        disabled_notice = '<div style="padding:12px; background:rgba(255,201,115,.15); border:1px solid rgba(255,201,115,.3); border-radius:10px; color:#ffc973; margin-bottom:15px;">เคสนี้ถูกปิดใช้งาน แต่ข้อมูลยังคงถูกเก็บไว้เป็นประวัติและไม่ได้ถูกลบออกจากระบบ</div>'

    terms_text = (
        getattr(rec, "warranty_terms", None)
        or getattr(rec, "action_taken", None)
        or getattr(rec, "summary", None)
        or "ความคุ้มครองโครงสร้างที่นอนและระบบสปริงตามเงื่อนไขมาตรฐานการรับประกันสินค้า"
    )

    created_date = str(rec.created_at)[:10] if getattr(rec, "created_at", None) else str(w_start)

    # --- 7. แทนที่ค่าลงใน HTML ---
    replacements = {
        "{{ record.warranty_number or ('WR-' ~ '%06d'|format(record.id)) }}": w_number,
        "{{ record.warranty_number or ('WR-' ~ '%06d' | format(record.id)) }}": w_number,
        "{% set ws = record.warranty_status or 'unknown' %}": "",
        "{% if ws == 'active' %}● อยู่ในประกัน{% elif ws == 'expired' %}● หมดประกัน{% else %}● ยังระบุสถานะไม่ได้{% endif %}": f"● {status_badge}",
        "{% if not record.is_active %}": disabled_notice,
        "{% endif %}": "",
        "เคสนี้ถูกปิดใช้งาน แต่ข้อมูลยังคงถูกเก็บไว้เป็นประวัติและไม่ได้ถูกลบออกจากระบบ": "",
        "{{ record.firstname or '-' }}": str(fname),
        "{{ record.lastname or '' }}": str(lname),
        "{{ record.customer_phone or '-' }}": rec.customer_phone or (phone if phone else "08X-XXX-XXXX"),
        "{{ record.brand or '-' }}": str(detected_brand),
        "{{ record.product_name or '-' }}": str(product_name_val),
        "{{ record.serial_number or '-' }}": str(serial_val),
        "{{ record.purchase_date or '-' }}": str(purchase_date_val),
        "{{ record.warranty_duration or '-' }}": str(duration_val),
        "{{ record.start_date or record.purchase_date or '-' }}": str(w_start),
        "{{ record.warranty_end_date or record.end_date or '-' }}": str(w_end),
        "{{ record.id }}": str(rec.id),
        "{{ record.filename or '-' }}": rec.filename or "-",
        "{{ record.assigned_agent_code or record.agent_code or '-' }}": str(agent_val),
        "{{ record.call_count or 0 }}": str(total_calls),
        "{{ record.warranty_terms or record.action_taken or record.summary or 'ไม่มีรายละเอียดเพิ่มเติมในระบบ' }}": terms_text,
        "{{ record.created_at[:10] if record.created_at else '-' }}": created_date
    }

    for target, value in replacements.items():
        html_content = html_content.replace(target, value)

    html_content = re.sub(r"\{\%.*?\%\}", "", html_content)
    return HTMLResponse(content=html_content)

@app.get("/add-customer", response_class=HTMLResponse)
@app.get("/add_customer", response_class=HTMLResponse)
def add_customer_page():
    return _render_template("add_customer.html")


@app.get("/permissions", response_class=HTMLResponse)
@app.get("/employees", response_class=HTMLResponse)
def permissions_page():
    return _render_template("permissions.html")


@app.get("/permission-matrix", response_class=HTMLResponse)
@app.get("/permission_matrix", response_class=HTMLResponse)
def permission_matrix_page():
    return _render_template("permission_matrix.html")


@app.get("/system-settings", response_class=HTMLResponse)
@app.get("/system_settings", response_class=HTMLResponse)
def system_settings_page():
    return _render_template("system_settings.html")


@app.get("/result", response_class=HTMLResponse)
@app.get("/view_result", response_class=HTMLResponse)
def result_page():
    for f in ("result.html", "view_result.html"):
        if os.path.exists(os.path.join(TEMPLATES_DIR, f)):
            return _render_template(f)
    return _render_template("dashboard.html")


# ==========================================
# 🎯 API ENDPOINTS
# ==========================================
@app.get("/api/permissions")
def get_permissions_matrix():
    return {"permissions": load_permissions_matrix()}


@app.put("/api/permissions")
async def update_permissions(request: Request):
    try:
        payload = await request.json()
        new_perms = payload.get("permissions", {})
        
        current_list = load_permissions_matrix()
        updated_list = []
        for item in current_list:
            key = item["key"]
            if key in new_perms:
                item["staff"] = bool(new_perms[key].get("staff", False))
                item["supervisor"] = bool(new_perms[key].get("supervisor", False))
                item["it"] = True
            updated_list.append(item)
            
        matrix_file = os.path.join(BASE_DIR, "permission_matrix.json")
        with open(matrix_file, "w", encoding="utf-8") as f:
            json.dump({"permissions": updated_list}, f, ensure_ascii=False, indent=2)
            
        return {"status": "success", "permissions": updated_list}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"ไม่สามารถบันทึกสิทธิ์ได้: {str(e)}")


@app.get("/api/system-settings")
def get_system_settings():
    return load_system_settings()

@app.put("/api/system-settings")
@app.post("/api/system-settings")
async def save_system_settings(request: Request):
    try:
        data = await request.json()
        settings_path = os.path.join(BASE_DIR, "system_settings.json")
        with open(settings_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return {"status": "success", "settings": data}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"ไม่สามารถบันทึกการตั้งค่าได้: {str(e)}")


@app.post("/api/cases/send-discord-direct")
async def send_discord_direct(request: Request):
    try:
        case_data = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    ref_id = str(case_data.get("id") or case_data.get("ref_id") or "1")
    target_channel_id = case_data.get("channel_id") or os.getenv("DISCORD_CHANNEL_ID")

    if not target_channel_id:
        raise HTTPException(status_code=400, detail="ไม่พบ DISCORD_CHANNEL_ID ใน .env")

    if not send_interactive_case_alert:
        return {"success": False, "message": "Discord service not configured"}

    success = await send_interactive_case_alert(
        channel_id=int(target_channel_id),
        case_id=ref_id,
        brand=case_data.get("brand") or "Unknown",
        customer_phone=case_data.get("customer_phone") or "-",
        score=str(case_data.get("agent_score") or case_data.get("score") or "-"),
        issue=case_data.get("issue") or "-",
        summary=case_data.get("summary") or "-",
    )

    if not success:
        raise HTTPException(
            status_code=500,
            detail="Discord API ปฏิเสธคำขอ ตรวจสอบสิทธิ์ของบอทในห้องเซิร์ฟเวอร์"
        )

    return {"success": True, "message": "ส่งเข้า Discord พร้อมปุ่มกดสำเร็จ"}


@app.post("/upload")
async def upload_audio_file(file: UploadFile = File(...), db: Session = Depends(get_db)):
    try:
        file_path = os.path.join(UPLOAD_DIR, file.filename)
        content = await file.read()
        with open(file_path, "wb") as buffer:
            buffer.write(content)

        file_hash = hashlib.md5(content).hexdigest()
        existing = (
            db.query(CallRecord)
            .filter((CallRecord.file_hash == file_hash) | (CallRecord.filename == file.filename))
            .first()
        )

        if existing:
            existing.file_hash = file_hash
            existing.filename = file.filename
            existing.status = "pending"
            existing.is_active = True
            db.commit()
            db.refresh(existing)
            target_record_id = existing.id
            action_msg = f"ตรวจพบไฟล์เดิม (Record ID: {existing.id}) ส่งเข้าคิวประมวลผลใหม่เรียบร้อยแล้ว"
        else:
            new_record = CallRecord(
                filename=file.filename,
                file_hash=file_hash,
                status="pending",
                is_active=True,
                created_at=datetime.now(),
            )
            db.add(new_record)
            db.commit()
            db.refresh(new_record)
            target_record_id = new_record.id
            action_msg = "ส่งเข้าคิวประมวลผลเรียบร้อยแล้ว"

        audio_task_queue.put(file_path=file_path, record_id=target_record_id, filename=file.filename)
        return {
            "status": "queued",
            "file_id": target_record_id,
            "filename": file.filename,
            "message": action_msg,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"การอัปโหลดล้มเหลว: {str(e)}")


@app.get("/api/queue/status")
def get_queue_status():
    return audio_task_queue.list_status()


@app.post("/api/queue/reorder")
def reorder_queue(data: QueueReorder):
    success = audio_task_queue.move_item(data.record_id, data.direction)
    if not success:
        raise HTTPException(status_code=400, detail="ไม่สามารถเลื่อนคิวได้ หรือตำแหน่งสุดขอบแล้ว")
    return {"status": "success", "queue": audio_task_queue.list_status()}


@app.post("/api/login")
async def login(request: Request, db: Session = Depends(get_db)):
    try:
        body = await request.json()
    except Exception:
        body = dict(await request.form())
    login_id = body.get("agent_code") or body.get("username") or body.get("email")
    password = body.get("password")
    if not login_id or not password:
        raise HTTPException(status_code=400, detail="กรุณากรอกข้อมูลให้ครบถ้วน")
    agent = db.query(Agent).filter((Agent.agent_code == login_id) | (Agent.email == login_id)).first()
    if not agent or agent.password != password:
        raise HTTPException(status_code=401, detail="รหัสพนักงานหรือรหัสผ่านไม่ถูกต้อง")
    if not bool(agent.is_active):
        raise HTTPException(status_code=403, detail="บัญชีนี้ถูกปิดใช้งาน")

    role = (agent.role or "staff").lower()
    response = JSONResponse({
        "status": "success",
        "agent_code": agent.agent_code,
        "role": role,
        "firstname": agent.firstname,
        "position": agent.position,
        "redirect": "/employees" if role == "it" else "/dashboard",
    })
    timeout = int(load_system_settings().get("session_timeout", 8) or 8)
    response.set_cookie(
        AUTH_COOKIE,
        _make_auth_token(agent.agent_code),
        httponly=True,
        samesite="lax",
        secure=os.getenv("CALLCENTER_COOKIE_SECURE", "0") == "1",
        max_age=max(1, timeout) * 3600,
    )
    return response


@app.post("/api/logout")
def logout():
    response = JSONResponse({"status": "success"})
    response.delete_cookie(
        key=AUTH_COOKIE,
        path="/",
        httponly=True,
        samesite="lax"
    )
    return response


@app.get("/api/me")
def me(request: Request, db: Session = Depends(get_db)):
    agent = _auth_agent(request, db)
    if not agent:
        raise HTTPException(status_code=401, detail="กรุณาเข้าสู่ระบบ")
    role = (agent.role or "staff").lower()
    return {
        "agent_code": agent.agent_code,
        "firstname": agent.firstname,
        "lastname": agent.lastname,
        "role": role,
        "position": agent.position,
        "is_active": bool(agent.is_active),
        "permissions": {p["key"]: bool(p.get(role, False)) for p in _permission_matrix()},
    }


@app.get("/api/agents")
@app.get("/api/employees")
def agents(db: Session = Depends(get_db)):
    rows = db.query(Agent).order_by(Agent.created_at.asc()).all()
    return [
        {
            "id": a.id,
            "agent_code": a.agent_code,
            "firstname": a.firstname,
            "lastname": a.lastname,
            "nickname": a.nickname,
            "role": a.role,
            "age": a.age,
            "gender": a.gender,
            "address": a.address,
            "phone": a.phone,
            "email": a.email,
            "emergency_contact": a.emergency_contact,
            "department": a.department,
            "position": a.position,
            "start_work_date": a.start_work_date,
            "is_active": bool(a.is_active),
        }
        for a in rows
    ]


@app.post("/api/agents")
def create_agent(data: AgentCreate, db: Session = Depends(get_db)):
    role = (data.role or "staff").strip().lower()
    if role not in {"staff", "supervisor", "it"}:
        raise HTTPException(status_code=400, detail="Role ไม่ถูกต้อง")
    if db.query(Agent).filter(Agent.agent_code == data.agent_code.strip()).first():
        raise HTTPException(status_code=400, detail="รหัสพนักงานนี้มีอยู่ในระบบแล้ว")
    row = Agent(
        agent_code=data.agent_code.strip(),
        password=data.password,
        firstname=data.firstname,
        lastname=data.lastname,
        nickname=data.nickname,
        role=role,
        age=data.age,
        gender=data.gender,
        address=data.address,
        phone=data.phone,
        email=data.email,
        emergency_contact=data.emergency_contact,
        department=data.department,
        position=data.position,
        start_work_date=data.start_work_date,
        is_active=True,
        created_at=datetime.now(),
    )
    db.add(row)
    db.commit()
    return {"status": "success", "agent_code": row.agent_code}


# 🛠️ ปรับให้รองรับทั้ง PUT, POST และ Map ค่าภาษาไทยเป็น role จริงในระบบ
@app.put("/api/agents/{agent_code}/role")
@app.put("/api/employees/{agent_code}/role")
@app.post("/api/agents/{agent_code}/role")
@app.post("/api/employees/{agent_code}/role")
async def update_role(agent_code: str, request: Request, db: Session = Depends(get_db)):
    try:
        body = await request.json()
    except Exception:
        body = dict(await request.form())

    raw_role = str(body.get("role", "")).strip().lower()

    # ตารางเทียบค่าภาษาไทยและชื่อเรียกต่างๆ แปลงกลับเป็นคีย์ฐานข้อมูล
    role_map = {
        "staff": "staff",
        "พนักงาน": "staff",
        "staff / พนักงาน": "staff",
        "supervisor": "supervisor",
        "หัวหน้า": "supervisor",
        "supervisor / หัวหน้า": "supervisor",
        "it": "it",
        "manager": "it",
        "หัวหน้างาน": "it",
        "manager / หัวหน้างาน": "it"
    }
    new_role = role_map.get(raw_role, raw_role)

    if new_role not in {"staff", "supervisor", "it"}:
        raise HTTPException(status_code=400, detail=f"Role ไม่ถูกต้อง: {raw_role}")

    target = db.query(Agent).filter(Agent.agent_code == agent_code).first()
    if not target:
        raise HTTPException(status_code=404, detail="ไม่พบพนักงานในระบบ")

    # บันทึก Role ใหม่
    target.role = new_role
    db.commit()
    db.refresh(target)
    return {"status": "success", "agent_code": agent_code, "role": new_role}


# 🛠️ ปรับปุ่ม Disable/Enable รองรับทั้ง PUT, POST และเปิด/ปิดได้จริง
@app.put("/api/agents/{agent_code}/status")
@app.put("/api/employees/{agent_code}/status")
@app.post("/api/agents/{agent_code}/status")
@app.post("/api/employees/{agent_code}/status")
async def update_agent_status(agent_code: str, request: Request, db: Session = Depends(get_db)):
    try:
        body = await request.json()
    except Exception:
        body = dict(await request.form())

    enabled = body.get("enabled")
    if enabled is None:
        enabled = body.get("is_active")

    target = db.query(Agent).filter(Agent.agent_code == agent_code).first()
    if not target:
        raise HTTPException(status_code=404, detail="ไม่พบพนักงานในระบบ")

    # ถ้าไม่มีค่าส่งมา ให้สลับสถานะจากเดิมอัตโนมัติ
    if enabled is None:
        target.is_active = not bool(target.is_active)
    else:
        target.is_active = bool(enabled)

    db.commit()
    db.refresh(target)
    return {"status": "success", "agent_code": target.agent_code, "is_active": bool(target.is_active)}


@app.get("/api/transfer-targets")
def transfer_targets(db: Session = Depends(get_db)):
    rows = db.query(Agent).filter(Agent.is_active.is_(True), Agent.role.in_(["staff", "supervisor"])).order_by(Agent.agent_code).all()
    return [{"agent_code": a.agent_code, "firstname": a.firstname, "lastname": a.lastname, "role": a.role} for a in rows]


@app.get("/stats")
def stats(db: Session = Depends(get_db)):
    base = db.query(CallRecord).filter(~CallRecord.filename.like("manual_%"), CallRecord.is_active.is_(True))
    topics = (
        db.query(CallRecord.issue, func.count(CallRecord.id))
        .filter(~CallRecord.filename.like("manual_%"), CallRecord.is_active.is_(True), CallRecord.issue.isnot(None), CallRecord.issue != "")
        .group_by(CallRecord.issue)
        .order_by(func.count(CallRecord.id).desc())
        .limit(6)
        .all()
    )
    return {
        "total": base.count(),
        "happy": base.filter(CallRecord.sentiment_score >= 60).count(),
        "escalated": base.filter(CallRecord.sentiment_score <= 40, CallRecord.sentiment_score > 0).count(),
        "anomaly_count": base.filter(CallRecord.anomaly_flag == "yes").count(),
        "agent_quality_avg": round(float(base.filter(CallRecord.agent_score > 0).with_entities(func.avg(CallRecord.agent_score)).scalar() or 0), 2),
        "topic_distribution": [{"topic": topic, "count": int(count)} for topic, count in topics],
    }
    
# 🛠️ ปรับแยกข้อมูลลูกค้าตามสถานะเปิด/ปิด (state: enabled / disabled)
@app.get("/api/customers")
def customers(state: str = "enabled", db: Session = Depends(get_db)):
    is_target_active = (state.lower() != "disabled")

    records = db.query(CallRecord).filter(
        CallRecord.is_active.is_(is_target_active),
        CallRecord.customer_phone.isnot(None),
        CallRecord.customer_phone != "",
        CallRecord.customer_phone != "Unknown"
    ).order_by(CallRecord.created_at.desc()).all()

    # จัดกลุ่มตามเบอร์โทรศัพท์
    customer_groups = {}
    for r in records:
        phone_clean = normalize_phone_number(r.customer_phone)
        if not phone_clean:
            continue
        if phone_clean not in customer_groups:
            customer_groups[phone_clean] = []
        customer_groups[phone_clean].append(r)

    result = []
    for phone_clean, call_list in customer_groups.items():
        # ดึงแบรนด์ที่ชัดเจนที่สุดจากทุกสายของลูกค้ารายนี้
        best_brand = next((c.brand for c in call_list if c.brand and c.brand not in ["Unknown", "-", ""]), "ลูกค้า")
        
        # นำสายล่าสุดมาเป็นตัวแทน
        latest_record = call_list[0]
        data = record_to_dict(latest_record)
        
        # ปรับชื่อลูกค้าให้ใช้ best_brand เสมอ
        if not data["firstname"] or data["firstname"] in ["-", "Unknown", "", "ลูกค้า"]:
            last_digits = phone_clean[-4:] if len(phone_clean) >= 4 else phone_clean
            data["brand"] = best_brand
            data["firstname"] = f"{best_brand}"
            data["lastname"] = f"({last_digits})"

        result.append(data)

    return result

# 🛠️ ปรับแยกไฟล์เสียงตามสถานะเปิด/ปิด (state: enabled / disabled)
@app.get("/files")
def files(state: str = "enabled", db: Session = Depends(get_db)):
    is_target_active = (state.lower() != "disabled")
    rows = db.query(CallRecord).filter(
        ~CallRecord.filename.like("manual_%"),
        CallRecord.is_active.is_(is_target_active)
    ).order_by(CallRecord.created_at.desc()).all()
    return [record_to_dict(r) for r in rows]


@app.get("/api/history/{phone}")
def history(phone: str, db: Session = Depends(get_db)):
    normalized = normalize_phone_number(phone)
    if not normalized:
        return []
    rows = db.query(CallRecord).filter(CallRecord.customer_phone == normalized).order_by(CallRecord.created_at.desc()).all()
    return [record_to_dict(r) for r in rows]


@app.get("/status/{file_id}")
def status(file_id: int, db: Session = Depends(get_db)):
    row = db.query(CallRecord).filter(CallRecord.id == file_id).first()
    return record_to_dict(row) if row else {"status": "not_found"}


# 🛠️ สลับสถานะเปิด/ปิดเคส พร้อมอัปเดตทุกสายของลูกค้ารายนั้น
@app.post("/api/cases/{file_id}/status")
async def case_status(file_id: int, request: Request, db: Session = Depends(get_db)):
    status_val = None
    phone_val = None
    try:
        data = await request.json()
        status_val = data.get("status")
        phone_val = data.get("phone")
    except Exception:
        pass

    if not status_val:
        try:
            form = await request.form()
            status_val = form.get("status")
            phone_val = form.get("phone")
        except Exception:
            pass

    target_active = (str(status_val).lower() == "enabled")
    target_status = "done" if target_active else "disabled"

    row = db.query(CallRecord).filter(CallRecord.id == file_id).first()
    target_phone = phone_val or (row.customer_phone if row else None)

    if target_phone:
        clean_phone = normalize_phone_number(target_phone)
        db.query(CallRecord).filter(
            (CallRecord.customer_phone == target_phone) | 
            (CallRecord.customer_phone == clean_phone)
        ).update({
            CallRecord.is_active: target_active,
            CallRecord.status: target_status
        }, synchronize_session=False)
    elif row:
        row.is_active = target_active
        row.status = target_status

    db.commit()
    return {"status": "success", "is_active": target_active}


@app.post("/api/cases/{file_id}/transfer")
def transfer(file_id: int, data: CaseTransfer, db: Session = Depends(get_db)):
    row = db.query(CallRecord).filter(CallRecord.id == file_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="ไม่พบข้อมูลเคส")
    if not bool(row.is_active):
        raise HTTPException(status_code=400, detail="กรุณา Enable เคสก่อนส่งต่อ")
    target = db.query(Agent).filter(Agent.agent_code == data.assigned_agent_code.strip(), Agent.is_active.is_(True)).first()
    if not target:
        raise HTTPException(status_code=404, detail="ไม่พบพนักงานปลายทาง")
    row.assigned_agent_code = target.agent_code
    db.commit()
    return {"status": "success", "file_id": file_id, "assigned_agent_code": target.agent_code}


@app.get("/healthz")
def healthz():
    return {"status": "ok", "service": "callcenter-ai"}


@app.get("/readyz")
def readyz(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        return {"status": "ready"}
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"database unavailable: {exc}")


@app.post("/api/cases/{file_id}/reprocess")
def reprocess_case(file_id: int, db: Session = Depends(get_db)):
    record = db.query(CallRecord).filter(CallRecord.id == file_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="ไม่พบข้อมูลเคส")
    file_path = os.path.join(UPLOAD_DIR, record.filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=400, detail="ไม่พบไฟล์เสียงต้นฉบับ")
    record.status = "pending"
    db.commit()
    audio_task_queue.put(file_path=file_path, record_id=record.id, filename=record.filename)
    return {"status": "success", "message": f"ส่งไฟล์ {record.filename} เข้าคิวประมวลผลใหม่เรียบร้อยแล้ว", "file_id": record.id}


@app.get("/download/{file_id}")
def download_audio_file(file_id: int, db: Session = Depends(get_db)):
    record = db.query(CallRecord).filter(CallRecord.id == file_id).first()
    if not record or not record.filename:
        raise HTTPException(status_code=404, detail="ไม่พบข้อมูลไฟล์เสียงในฐานข้อมูล")
    file_path = os.path.join(UPLOAD_DIR, record.filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="ไม่พบไฟล์เสียงในเซิร์ฟเวอร์")
    media_type = "audio/wav" if record.filename.lower().endswith(".wav") else "audio/mpeg"
    return FileResponse(path=file_path, media_type=media_type, filename=record.filename)


@app.get("/export/csv")
def export_csv(year: str | None = None, quarter: str | None = None, month: str | None = None, db: Session = Depends(get_db)):
    rows = db.query(CallRecord).filter(CallRecord.is_active.is_(True)).all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Phone", "Firstname", "Lastname", "Brand", "Issue", "Summary", "Sentiment Score", "Agent Score", "Anomaly", "Date"])
    for r in rows:
        writer.writerow([
            r.customer_phone or "",
            r.firstname or "",
            r.lastname or "",
            r.brand or "",
            r.issue or "",
            r.summary or "",
            r.sentiment_score or 0,
            r.agent_score or 0,
            r.anomaly_flag or "no",
            r.created_at.strftime("%Y-%m-%d %H:%M:%S") if r.created_at else ""
        ])
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue().encode("utf-8-sig")]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=call_cases.csv"}
    )

@app.get("/export/json")
def export_json(db: Session = Depends(get_db)):
    """คืนค่าข้อมูลเคสทั้งหมดในรูปแบบ JSON สำหรับระบบแท็บและประวัติของหน้าลูกค้า"""
    rows = db.query(CallRecord).order_by(CallRecord.created_at.desc()).all()
    return {
        "status": "success",
        "total": len(rows),
        "records": [record_to_dict(r) for r in rows]
    }

# ==========================================
## ==========================================
# 🚨 URGENT & VVIP WAR ROOM API
# ==========================================

@app.get("/urgent-cases", response_class=HTMLResponse)
def urgent_cases_page():
    return _render_template("urgent_cases.html")


@app.get("/api/urgent-cases")
def get_urgent_cases(db: Session = Depends(get_db)):
    """ดึงเฉพาะเคสที่เข้าเงื่อนไขด่วน / VVIP หรือเคสที่มีการมอบหมายงาน"""
    try:
        records = db.query(CallRecord).filter(
            CallRecord.is_active.is_(True),
            ~CallRecord.filename.like("manual_%")
        ).order_by(CallRecord.created_at.desc()).all()

        urgent_list = []
        for r in records:
            score = float(r.sentiment_score or 60)
            brand = str(r.brand or "").strip().lower()
            anomaly = str(r.anomaly_flag or "").strip().lower()
            assigned = str(r.assigned_agent_code or getattr(r, "handled_by", "") or "").strip()
            priority = str(getattr(r, "priority", "") or "").strip().lower()

            # เงื่อนไข: VVIP (Omazz), เคสด่วน (คะแนน <= 50 หรือ anomaly), หรือมีคนกดรับงานแล้ว
            is_vvip = (priority == "vvip") or (brand == "omazz")
            is_urgent = (priority == "urgent") or (score <= 50 and score > 0) or (anomaly == "yes")
            is_claimed = bool(assigned)

            if is_vvip or is_urgent or is_claimed:
                data = record_to_dict(r)
                if is_vvip:
                    data["priority"] = "vvip"
                urgent_list.append(data)

        return urgent_list

    except Exception as e:
        print(f"❌ [Urgent API Error]: {e}")
        return []


class ClaimCasePayload(BaseModel):
    agent_code: str
    priority: str | None = None


# ตัวอย่างใน backend/main.py ตรงจุดรับเคส
@app.post("/api/urgent-cases/{case_id}/claim")
async def claim_urgent_case(case_id: int, payload: dict, db: Session = Depends(get_db)):
    agent_code = payload.get("agent_code")
    
    record = db.query(CallRecord).filter(CallRecord.id == case_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Case not found")

    record.assigned_agent_code = agent_code
    record.handled_by = agent_code
    record.handled_at = datetime.now()
    record.case_stage = "in_progress"   # สถานะคือ กำลังดำเนินการ (ยังไม่ปิด)
    record.status = "in_progress"        # ป้องกันไม่ให้คอลัมน์ status กลายเป็น done
    db.commit()

    try:
        from backend.discord_bot_service import trigger_discord_claim_notification
        trigger_discord_claim_notification(case_id, agent_code)
    except Exception as e:
        print(f"Discord notify error: {e}")

    return {"success": True, "message": f"มอบหมายเคสให้ {agent_code} เรียบร้อยแล้ว"}


@app.get("/api/urgent-cases/export-performance")
def export_urgent_performance(db: Session = Depends(get_db)):
    """Export สรุปผลงานรายบุคคล พร้อมรายชื่อลูกค้าที่ปิดเคสสำเร็จ"""
    import io, csv
    from fastapi.responses import Response

    output = io.StringIO()
    writer = csv.writer(output)

    # เขียน Header 8 คอลัมน์ชัดเจน
    writer.writerow([
        "อันดับ",
        "ชื่อพนักงาน",
        "รหัสพนักงาน",
        "เคสที่ได้รับ",
        "เคสที่ปิดสำเร็จ",
        "คะแนนบริการเฉลี่ย",
        "ความพึงพอใจลูกค้าเฉลี่ย (%)",
        "รายชื่อลูกค้าที่ปิดเคสสำเร็จ"
    ])

    agents = db.query(Agent).filter(Agent.is_active == True).all()
    summary = []

    for agent in agents:
        assigned = db.query(CallRecord).filter(
            CallRecord.assigned_agent_code == agent.agent_code,
            CallRecord.is_active == True
        ).all()

        # เคสที่ปิดสำเร็จ: เช็คทั้ง status = 'done', 'closed' หรือ case_stage = 'resolved' หรือมี closed_by
        closed = [
            r for r in assigned 
            if getattr(r, "status", "") in ["done", "closed", "ปิดเคสสำเร็จ"]
            or getattr(r, "case_stage", "") in ["resolved", "closed"]
            or getattr(r, "closed_by", None) is not None
        ]

        closed_names = []
        for r in closed:
            fn = getattr(r, "firstname", "") or ""
            ln = getattr(r, "lastname", "") or ""
            name = f"{fn} {ln}".strip() or getattr(r, "brand", "") or "ลูกค้า"
            phone = getattr(r, "customer_phone", "") or "-"
            brand = getattr(r, "brand", "") or "ทั่วไป"
            closed_names.append(f"#{r.id} {name} ({phone}) [{brand}]")

        closed_str = " ; ".join(closed_names) if closed_names else "—"

        scores = [float(r.agent_score or 0) for r in assigned if getattr(r, "agent_score", None)]
        sentiments = [float(r.sentiment_score or 0) for r in assigned if getattr(r, "sentiment_score", None)]

        avg_score = round(sum(scores) / len(scores), 1) if scores else 0
        avg_sentiment = round(sum(sentiments) / len(sentiments)) if sentiments else 0

        summary.append({
            "name": f"{getattr(agent, 'firstname', '') or ''} {getattr(agent, 'lastname', '') or ''}".strip() or agent.agent_code,
            "code": agent.agent_code,
            "assigned": len(assigned),
            "closed": len(closed),
            "score": avg_score,
            "sentiment": avg_sentiment,
            "closed_str": closed_str
        })

    # เรียงลำดับตามเคสที่ปิดสำเร็จและคะแนน
    summary.sort(key=lambda x: (x["closed"], x["score"]), reverse=True)

    for idx, item in enumerate(summary, 1):
        writer.writerow([
            idx,
            item["name"],
            item["code"],
            item["assigned"],
            item["closed"],
            item["score"],
            item["sentiment"],
            item["closed_str"]
        ])

    csv_data = "﻿" + output.getvalue()
    return Response(
        content=csv_data,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=agent_performance_closed_cases.csv"}
    )
