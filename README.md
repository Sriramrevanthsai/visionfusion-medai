# VisionFusion MedAI

Voice, vision, and text intelligence for healthcare workflows.

VisionFusion MedAI is a FastAPI-based multimodal healthcare assistant designed around MedGemma, MedASR, prescription OCR, and MCP-style tool orchestration. The current build includes a polished static web UI, login/register flow, medical case intake, image/audio upload, risk triage, doctor/patient output modes, follow-up question handling, case history, and downloadable PDF reports.

## Run

```powershell
cd visionfusion-medai
python -m uvicorn backend.main:app --reload --port 8000
```

Then open:

```text
http://127.0.0.1:8000
```

## Current Workflow

1. Login, register as a patient, or open a demo doctor/admin account.
2. Choose Doctor mode or Patient mode. Patient accounts are automatically kept in Patient mode.
3. Choose a workflow: general multimodal reasoning, prescription, wound follow-up, radiology-style explanation, or clinical documentation.
4. Enter symptoms / clinical notes and upload image or audio files when available.
5. Generate the insight.
6. If the result says more information is needed, the warning panel now shows the exact follow-up questions inside the same box.
7. Ask the patient those questions, enter the answers in the Follow-up answers / extra patient details box, and regenerate the insight.
8. Download the PDF report after doctor review.

## Follow-Up Question Behavior

The app checks whether clinically important information is missing before giving stronger guidance. For example, knee cases look for pain score, swelling or redness, injury history, walking ability, and medical risk factors. When any of these are missing, the result panel shows:

- what information is missing
- the exact follow-up questions to ask the patient
- instructions to enter the answers in the follow-up answers box and regenerate

This keeps the original symptoms separate from the second-round patient answers while still combining both inputs in the backend before reasoning.

## Automatic Multi-Model Routing

The app selects the model option automatically from the logged-in user role, selected workflow, and uploaded inputs. The current project still uses deterministic demo adapters so it works immediately without GPU credentials, but the selected route is carried through the API response, result card, audit trail, and PDF report.

| Option | Use |
|---|---|
| Demo hybrid adapter | Current local demo pipeline for image features, risk scoring, follow-up questions, SOAP notes, safety checks, and PDF reports. |
| MedGemma 4B multimodal | Local or limited-GPU medical image + text reasoning for development, demos, and privacy-first clinic workflows. |
| MedGemma 27B multimodal | Preferred production model for higher-quality medical image, prescription, radiology, and symptom reasoning through cloud or dedicated GPU deployment. |
| MedASR voice pipeline | Medical speech-to-text for doctor dictation, patient conversations, and clinical note generation. |
| Prescription OCR + MedGemma | Reads medicine names, strengths, routes, dosage timing, duration, and precautions from prescription or medicine-label images. |
| MCP tool router | Coordinates specialist tools for image inspection, transcription, retrieval, risk scoring, report generation, image comparison, and audit trails. |

Routing rules in the demo:

- Prescription workflow uses Prescription OCR + MedGemma.
- Clinical note workflow or uploaded audio uses MedASR.
- Doctor-mode image, radiology, or wound cases use MedGemma 27B multimodal.
- Patient image cases use MedGemma 4B multimodal.
- Text-only patient cases use the demo hybrid adapter.
- Tool-heavy doctor/admin cases can route to the MCP tool router.

## User Roles and Admin Rules

Patients can create their own accounts from the Register tab. Doctors and admins cannot self-register; they must be created by an admin.

Default demo accounts:

| Account | Password | Role |
|---|---|---|
| `admin@visionfusion.ai` | `admin123` | Admin |
| `doctor@visionfusion.ai` | `demo123` | Doctor |

Admin capabilities:

- view all users
- create doctor, patient, or admin users
- delete users
- cannot delete the currently logged-in admin account

## API Endpoints

| Endpoint | Method | Purpose |
|---|---|---|
| `/api/auth/register` | POST | Patient self-registration only |
| `/api/auth/login` | POST | Authenticate existing users |
| `/api/demo-user` | GET | Open a demo doctor workspace |
| `/api/demo-admin` | GET | Open a demo admin workspace |
| `/api/admin/users` | GET | Admin-only list of users |
| `/api/admin/users` | POST | Admin-only user creation |
| `/api/admin/users/{email}` | DELETE | Admin-only user deletion |
| `/api/cases/analyze` | POST | Upload image/audio/text and generate multimodal insight |
| `/api/cases` | GET | Retrieve case history |
| `/api/cases/{case_id}/report` | GET | Download case PDF report |

## Implementation Notes

- Backend entry point: `backend/main.py`
- Model adapter layer: `backend/services/model_adapters.py`
- PDF report generator: `backend/services/reporting.py`
- Frontend page: `frontend/index.html`
- Frontend logic: `frontend/static/app.js`
- Frontend styling: `frontend/static/styles.css`

To connect real models, keep the API contract stable and replace the deterministic functions in `backend/services/model_adapters.py` with MedGemma, MedASR, OCR, retrieval, or cloud endpoint calls.
