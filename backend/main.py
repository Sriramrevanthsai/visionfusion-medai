from __future__ import annotations

import shutil
import uuid
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles

from .services.model_adapters import (
    extract_image_features,
    extract_prescription_from_image,
    generate_medical_reasoning,
    transcribe_medical_audio,
)
from .services.reporting import build_case_pdf

BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"
UPLOAD_DIR = BASE_DIR / "storage" / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="VisionFusion MedAI", version="0.1.0")

USERS: dict[str, dict] = {}
CASES: dict[str, dict] = {}
USERS.update(
    {
        "admin@visionfusion.ai": {
            "name": "VisionFusion Admin",
            "email": "admin@visionfusion.ai",
            "password": "admin123",
            "role": "admin",
        },
        "doctor@visionfusion.ai": {
            "name": "Dr. Aarya Mehta",
            "email": "doctor@visionfusion.ai",
            "password": "demo123",
            "role": "doctor",
        },
    }
)

app.mount("/static", StaticFiles(directory=FRONTEND_DIR / "static"), name="static")


@app.get("/")
def index() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "index.html")


@app.post("/api/auth/register")
async def register(name: str = Form(...), email: str = Form(...), password: str = Form(...), role: str = Form("patient")):
    email = email.lower().strip()
    if email in USERS:
        raise HTTPException(status_code=409, detail="Account already exists")
    if role != "patient":
        raise HTTPException(status_code=403, detail="Patients can self-register. Doctors and admins must be created by an admin.")
    USERS[email] = {"name": name.strip(), "email": email, "password": password, "role": "patient"}
    return {"token": email, "user": _public_user(USERS[email])}


@app.post("/api/auth/login")
async def login(email: str = Form(...), password: str = Form(...)):
    email = email.lower().strip()
    user = USERS.get(email)
    if not user or user["password"] != password:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    return {"token": email, "user": _public_user(user)}


@app.get("/api/demo-user")
def demo_user():
    email = "doctor@visionfusion.ai"
    return {"token": email, "user": _public_user(USERS[email])}


@app.get("/api/demo-admin")
def demo_admin():
    email = "admin@visionfusion.ai"
    return {"token": email, "user": _public_user(USERS[email])}


@app.get("/api/admin/users")
def list_users(token: str):
    _require_admin(token)
    return [_public_user(user) for user in USERS.values()]


@app.post("/api/admin/users")
async def create_user(
    token: str = Form(...),
    name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    role: str = Form("doctor"),
):
    _require_admin(token)
    email = email.lower().strip()
    if role not in {"doctor", "patient", "admin"}:
        raise HTTPException(status_code=400, detail="Role must be doctor, patient, or admin")
    if email in USERS:
        raise HTTPException(status_code=409, detail="Account already exists")
    USERS[email] = {"name": name.strip(), "email": email, "password": password, "role": role}
    return _public_user(USERS[email])


@app.delete("/api/admin/users/{email}")
def delete_user(email: str, token: str):
    admin = _require_admin(token)
    email = email.lower().strip()
    if email == admin["email"]:
        raise HTTPException(status_code=400, detail="Admin cannot delete their own active account")
    if email not in USERS:
        raise HTTPException(status_code=404, detail="User not found")
    del USERS[email]
    return {"deleted": email}


@app.post("/api/cases/analyze")
async def analyze_case(
    token: str = Form(...),
    patient_name: str = Form(...),
    mode: str = Form("patient"),
    case_type: str = Form("general"),
    symptoms: str = Form(""),
    followup_answers: str = Form(""),
    prescription_text: str = Form(""),
    image: UploadFile | None = File(None),
    previous_image: UploadFile | None = File(None),
    audio: UploadFile | None = File(None),
):
    user = _require_user(token)
    mode = _case_mode_for_user(user, mode)
    case_id = f"VF-{uuid.uuid4().hex[:8].upper()}"
    case_dir = UPLOAD_DIR / case_id
    case_dir.mkdir(parents=True, exist_ok=True)

    image_path = await _save_upload(image, case_dir) if image and image.filename else None
    previous_image_path = await _save_upload(previous_image, case_dir) if previous_image and previous_image.filename else None
    audio_path = await _save_upload(audio, case_dir) if audio and audio.filename else None

    features = extract_image_features(image_path) if image_path else None
    previous_features = extract_image_features(previous_image_path) if previous_image_path else None
    prescription_extraction = extract_prescription_from_image(image_path) if case_type == "prescription" else {}
    transcript = transcribe_medical_audio(audio_path)
    combined_symptoms = "\n".join(part for part in [symptoms.strip(), followup_answers.strip()] if part)
    model_profile = _auto_model_profile(user=user, case_type=case_type, has_image=bool(image_path), has_audio=bool(audio_path), mode=mode)
    analysis = generate_medical_reasoning(
        features=features,
        symptoms=combined_symptoms,
        transcript=transcript,
        mode=mode,
        model_profile=model_profile,
        case_type=case_type,
        prescription_text=prescription_text,
        prescription_extraction=prescription_extraction,
        previous_features=previous_features,
    )

    case = {
        "id": case_id,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "patient_name": patient_name.strip(),
        "mode": mode,
        "model_profile": model_profile,
        "case_type": case_type,
        "symptoms": symptoms.strip(),
        "followup_answers": followup_answers.strip(),
        "prescription_text": prescription_text.strip(),
        "image_name": image.filename if image else "",
        "previous_image_name": previous_image.filename if previous_image else "",
        "audio_name": audio.filename if audio else "",
        "features": features.__dict__ if features else None,
        "previous_features": previous_features.__dict__ if previous_features else None,
        "transcript": transcript,
        "analysis": analysis,
        "audit": [
            "Case created",
            f"Automatic model routing selected: {analysis['model_profile']['label']}",
            "Image feature tool executed" if features else "Image feature tool skipped",
            "Previous image comparison tool executed" if previous_features else "Previous image comparison skipped",
            "MedASR adapter executed" if audio_path else "MedASR adapter skipped",
            "MedGemma reasoning adapter executed",
            "Report generator ready",
            "Doctor approval pending",
        ],
    }
    CASES[case_id] = case
    return case


@app.get("/api/cases")
def list_cases(token: str):
    _require_user(token)
    return list(CASES.values())[::-1]


@app.get("/api/cases/{case_id}/report")
def download_report(case_id: str, token: str):
    _require_user(token)
    case = CASES.get(case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    pdf = build_case_pdf(case)
    headers = {"Content-Disposition": f'attachment; filename="{case_id}-visionfusion-report.pdf"'}
    return Response(pdf, media_type="application/pdf", headers=headers)


def _public_user(user: dict) -> dict:
    return {"name": user["name"], "email": user["email"], "role": user["role"]}


def _require_user(token: str) -> dict:
    user = USERS.get(token.lower().strip())
    if not user:
        raise HTTPException(status_code=401, detail="Please login first")
    return user


def _require_admin(token: str) -> dict:
    user = _require_user(token)
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


def _case_mode_for_user(user: dict, requested_mode: str) -> str:
    if user["role"] == "patient":
        return "patient"
    if user["role"] in {"doctor", "admin"} and requested_mode in {"doctor", "patient"}:
        return requested_mode
    return "doctor"


def _auto_model_profile(*, user: dict, case_type: str, has_image: bool, has_audio: bool, mode: str) -> str:
    if case_type == "prescription":
        return "prescription_ocr"
    if case_type == "clinical_note" or has_audio:
        return "medasr"
    if user["role"] == "doctor" or mode == "doctor":
        return "medgemma_27b" if has_image or case_type in {"radiology", "wound"} else "mcp_tool_router"
    if user["role"] == "admin":
        return "mcp_tool_router"
    if has_image:
        return "medgemma_4b"
    return "demo_hybrid"


async def _save_upload(upload: UploadFile, case_dir: Path) -> Path:
    target = case_dir / f"{uuid.uuid4().hex}_{Path(upload.filename or 'upload').name}"
    with target.open("wb") as handle:
        shutil.copyfileobj(upload.file, handle)
    return target
