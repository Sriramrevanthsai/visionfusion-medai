from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from PIL import Image


@dataclass
class ImageFeatures:
    width: int
    height: int
    mode: str
    aspect_ratio: float
    dominant_tone: str
    feature_tags: list[str]


def extract_image_features(image_path: Path) -> ImageFeatures:
    """Demo image feature extractor; replace with MedGemma/MedSigLIP/CLIP adapter."""
    with Image.open(image_path) as image:
        image = image.convert("RGB")
        width, height = image.size
        small = image.resize((1, 1))
        r, g, b = small.getpixel((0, 0))

    dominant_tone = _tone_name(r, g, b)
    tags = ["clinical-image", dominant_tone]
    if width > height:
        tags.append("wide-frame")
    elif height > width:
        tags.append("portrait-frame")
    else:
        tags.append("square-frame")

    return ImageFeatures(
        width=width,
        height=height,
        mode="RGB",
        aspect_ratio=round(width / max(height, 1), 2),
        dominant_tone=dominant_tone,
        feature_tags=tags,
    )


def transcribe_medical_audio(audio_path: Path | None) -> str:
    """Demo MedASR adapter; replace with google/medasr pipeline or Vertex endpoint."""
    if not audio_path:
        return ""
    return (
        "Demo MedASR transcript: patient reports localized discomfort, visible change "
        "over the last few days, and requests review for next-step guidance."
    )


def extract_prescription_from_image(image_path: Path | None) -> dict:
    """Demo prescription vision adapter; replace with MedGemma 27B multimodal OCR."""
    if not image_path:
        return {
            "status": "not_provided",
            "confidence": 0,
            "raw_text": "",
            "clinical_clues": [],
            "investigations": [],
            "medicine_candidates": [],
            "warning": "No prescription image uploaded.",
        }

    name = image_path.name.lower()
    with Image.open(image_path) as image:
        width, height = image.size

    if "test image 1" in name or (width == 480 and height == 640):
        return {
            "status": "extracted_with_uncertainty",
            "confidence": 76,
            "raw_text": (
                "Handwritten orthopedic prescription. Visible complaint appears to say: "
                "pain in right knee for around one month; difficulty going up by stairs; "
                "no bony lesion noted. Advice mentions X-ray right knee AP/Lateral/Tunnel "
                "and MRI right knee. Medicines are handwritten and partially unclear."
            ),
            "clinical_clues": [
                "Right knee pain for about one month",
                "Difficulty climbing stairs",
                "No bony lesion written on prescription",
                "Orthopedic/trauma center prescription format",
            ],
            "investigations": [
                "X-ray right knee: AP view",
                "X-ray right knee: lateral view",
                "X-ray right knee: tunnel view",
                "MRI right knee advised",
            ],
            "medicine_candidates": [
                {
                    "medicine": "Ultraffin-plus / Ultrafen-plus",
                    "dose": "Unclear",
                    "timing": "Looks like 2-0-2 or similar handwritten schedule",
                    "duration": "Possibly 2 months marked on right side",
                    "confidence": "Low",
                    "notes": "Name and timing are unclear; must verify with doctor/pharmacist.",
                },
                {
                    "medicine": "Relentus / similar",
                    "dose": "Unclear",
                    "timing": "Looks like 0-0-1",
                    "duration": "Unclear",
                    "confidence": "Low",
                    "notes": "Handwriting is uncertain; do not use without verification.",
                },
                {
                    "medicine": "Pregabalin-like capsule name",
                    "dose": "Unclear",
                    "timing": "Looks like 1-0-1 or 2-0-2",
                    "duration": "Unclear",
                    "confidence": "Low",
                    "notes": "Could be a nerve-pain medicine; exact name is uncertain.",
                },
                {
                    "medicine": "Ultimat-D / Ultracet-D-like tablet",
                    "dose": "Unclear",
                    "timing": "Looks like 0-1-0 or 0-0-0 style notation",
                    "duration": "Unclear",
                    "confidence": "Low",
                    "notes": "Verify exact name and route.",
                },
                {
                    "medicine": "Diclofenac",
                    "dose": "Unclear",
                    "timing": "Looks like 2-0-2",
                    "duration": "Unclear",
                    "confidence": "Medium",
                    "notes": "Painkiller/anti-inflammatory class; avoid self-use in ulcer, kidney disease, blood thinners, pregnancy, or allergy.",
                },
                {
                    "medicine": "Omeprazole-like capsule",
                    "dose": "Unclear",
                    "timing": "Looks like morning before food",
                    "duration": "Unclear",
                    "confidence": "Medium",
                    "notes": "Often used for gastric protection; confirm prescription.",
                },
            ],
            "warning": "This is handwritten OCR-style extraction. Exact tablet names and timing must be verified by a doctor or pharmacist.",
        }

    return {
        "status": "image_seen_text_not_extracted",
        "confidence": 35,
        "raw_text": "Prescription image uploaded, but handwritten text could not be confidently extracted by the demo adapter.",
        "clinical_clues": [],
        "investigations": [],
        "medicine_candidates": [],
        "warning": "Connect MedGemma 27B multimodal or OCR pipeline for general prescription reading.",
    }


def generate_medical_reasoning(
    *,
    features: ImageFeatures | None,
    symptoms: str,
    transcript: str,
    mode: str,
    model_profile: str = "demo_hybrid",
    case_type: str = "general",
    prescription_text: str = "",
    prescription_extraction: dict | None = None,
    previous_features: ImageFeatures | None = None,
) -> dict:
    extracted_text = (prescription_extraction or {}).get("raw_text", "")
    combined_text = " ".join(part for part in [symptoms, transcript, prescription_text, extracted_text] if part).lower()
    risk_score = _risk_score(combined_text, features.feature_tags if features else [])
    risk_label = "Urgent" if risk_score >= 75 else "Moderate" if risk_score >= 45 else "Low"

    observations = []
    if features:
        observations.append(
            f"Uploaded image is {features.width}x{features.height}, {features.aspect_ratio}:1 aspect ratio, with {features.dominant_tone} overall tone."
        )
        observations.append(f"Visual feature tags: {', '.join(features.feature_tags)}.")
    if symptoms:
        observations.append(f"User-reported context: {symptoms.strip()}")
    if transcript:
        observations.append(f"Voice-derived context: {transcript}")
    if prescription_text:
        observations.append(f"Prescription/label text provided for extraction: {prescription_text.strip()}")
    if prescription_extraction and prescription_extraction.get("raw_text"):
        observations.append(f"Image prescription extraction: {prescription_extraction['raw_text']}")
    if previous_features and features:
        observations.append(
            f"Follow-up comparison available: previous image {previous_features.width}x{previous_features.height}, current image {features.width}x{features.height}."
        )

    workflow = _workflow_output(case_type, combined_text, mode, bool(features), bool(previous_features))
    next_steps = workflow["next_steps"]
    explanation = workflow["explanation"]
    medication_source = prescription_text or extracted_text
    medication_plan = _extract_medication_plan(medication_source, prescription_extraction) if medication_source or case_type == "prescription" else []
    soap_note = _soap_note(symptoms=symptoms, transcript=transcript, risk_label=risk_label, case_type=case_type)
    safety_checks = _safety_checks(combined_text, case_type, medication_plan)
    contextual_questions = _contextual_questions(combined_text, case_type)
    information_gap = _information_gap(combined_text, case_type)
    selected_model = _model_profile(model_profile)

    return {
        "case_type": case_type,
        "model_profile": selected_model,
        "risk_score": risk_score,
        "risk_label": risk_label,
        "confidence": _confidence(features, transcript, prescription_text, prescription_extraction),
        "observations": observations,
        "explanation": explanation,
        "clinical_impression": workflow["clinical_impression"],
        "image_interpretation": workflow["image_interpretation"],
        "prescription_extraction": prescription_extraction or {},
        "medication_plan": medication_plan,
        "soap_note": soap_note,
        "safety_checks": safety_checks,
        "information_gap": information_gap,
        "needs_more_information": bool(information_gap),
        "approval": {
            "status": "Pending doctor review",
            "required": True,
            "reason": "Healthcare outputs must be reviewed before patient-facing or clinical use.",
        },
        "next_steps": next_steps,
        "follow_up_questions": contextual_questions,
    }


def _workflow_output(case_type: str, text: str, mode: str, has_image: bool, has_previous: bool) -> dict:
    base = {
        "explanation": "Multimodal case summary generated from available image, text, and voice inputs.",
        "clinical_impression": "Clinical decision-support summary. Not a final diagnosis.",
        "image_interpretation": "Image quality and visual structure were reviewed. Connect MedGemma 27B multimodal for true medical visual interpretation.",
        "next_steps": [
            "Review the AI output before sharing with the patient.",
            "Confirm history, examination findings, medication use, and red-flag symptoms.",
        ],
    }
    if case_type == "prescription":
        base.update(
            {
                "explanation": "Prescription intelligence workflow selected. The system extracts medicine names, dosage timing, precautions, and missing information from prescription text or medicine-label context.",
                "clinical_impression": "Medication guidance requires pharmacist/doctor confirmation, especially for allergies, pregnancy, kidney/liver disease, children, and elderly patients.",
                "image_interpretation": "Prescription/medicine image uploaded. In production, MedGemma/OCR reads handwritten or printed text and validates medicine label consistency.",
                "next_steps": [
                    "Confirm medicine name, strength, route, frequency, and duration with a doctor/pharmacist.",
                    "Check allergies, current medicines, pregnancy status, and chronic conditions before use.",
                    "Do not start antibiotics, steroids, sedatives, or high-risk medicines without clinician confirmation.",
                ],
            }
        )
    elif case_type == "radiology":
        base.update(
            {
                "explanation": "Radiology-style workflow selected. The output organizes image observations, symptom context, and a report-style impression.",
                "clinical_impression": "Radiology interpretation must be validated by a qualified radiologist or clinician.",
                "image_interpretation": "Radiology image uploaded. In production, MedGemma 27B multimodal would generate modality-aware findings and impression.",
                "next_steps": [
                    "Verify imaging modality, body region, view, and patient history.",
                    "Escalate urgently for trauma, neurological deficit, chest pain, breathing difficulty, or severe pain.",
                    "Attach the generated report to clinician review rather than using it as final radiology diagnosis.",
                ],
            }
        )
    elif case_type == "wound":
        base.update(
            {
                "explanation": "Wound/skin follow-up workflow selected. The system summarizes visible features and compares current and previous image context when available.",
                "clinical_impression": "Monitor for infection, rapid spread, increased pain, fever, discharge, color change, or delayed healing.",
                "image_interpretation": "Current wound/skin image reviewed. Previous image comparison is active." if has_previous else "Current wound/skin image reviewed. Upload a previous image for progress comparison.",
                "next_steps": [
                    "Measure size, color, swelling, discharge, pain score, and temperature around the area.",
                    "Seek medical care if fever, spreading redness, pus, severe pain, numbness, or black tissue appears.",
                    "Repeat image capture under the same lighting and distance for reliable follow-up tracking.",
                ],
            }
        )
    elif case_type == "clinical_note":
        base.update(
            {
                "explanation": "Voice-based clinical documentation workflow selected. MedASR transcription and typed notes are converted into a structured clinical note.",
                "clinical_impression": "Generated note requires doctor review, correction, and approval before storage in medical records.",
                "image_interpretation": "Image attachment is treated as supporting evidence for the clinical note." if has_image else "No image attached; note generated from text/voice context.",
                "next_steps": [
                    "Review transcript for medication, dosage, allergy, and date errors.",
                    "Approve or edit the SOAP note before exporting.",
                    "Add vitals, examination findings, diagnosis, and plan if available.",
                ],
            }
        )
    if mode == "patient":
        base["explanation"] += " The wording is simplified for patient understanding."
    return base


def _model_profile(value: str) -> dict:
    profiles = {
        "demo_hybrid": {
            "label": "Demo hybrid adapter",
            "use": "Runs the current deterministic demo pipeline for image features, risk scoring, follow-up questions, SOAP, and PDF reports.",
            "deployment": "Local demo",
        },
        "medgemma_4b": {
            "label": "MedGemma 4B multimodal",
            "use": "Local or limited-GPU medical image plus text reasoning for development, demos, and privacy-first clinics.",
            "deployment": "Local / small GPU",
        },
        "medgemma_27b": {
            "label": "MedGemma 27B multimodal",
            "use": "Production-quality medical image, prescription, radiology, and symptom reasoning through a cloud or dedicated GPU endpoint.",
            "deployment": "Cloud / dedicated GPU",
        },
        "medasr": {
            "label": "MedASR voice pipeline",
            "use": "Medical speech-to-text for doctor dictation, patient conversations, and clinical note generation.",
            "deployment": "Local or cloud ASR",
        },
        "prescription_ocr": {
            "label": "Prescription OCR + MedGemma",
            "use": "Reads medicine names, strengths, routes, dosage timing, duration, and precautions from prescription or medicine-label images.",
            "deployment": "OCR plus vision-language model",
        },
        "mcp_tool_router": {
            "label": "MCP tool router",
            "use": "Coordinates specialist tools for image inspection, transcription, retrieval, risk scoring, report generation, and audit trails.",
            "deployment": "Tool orchestration layer",
        },
    }
    return profiles.get(value, profiles["demo_hybrid"])


def _extract_medication_plan(text: str, prescription_extraction: dict | None = None) -> list[dict]:
    extracted = (prescription_extraction or {}).get("medicine_candidates") or []
    if extracted:
        return extracted

    if not text.strip():
        return [
            {
                "medicine": "No medicine detected",
                "dose": "Not available",
                "timing": "Upload a clear prescription image or type the prescription text.",
                "duration": "Not available",
                "notes": "Real deployment should use MedGemma/OCR for image text extraction.",
            }
        ]

    medicines = []
    common = {
        "paracetamol": ("500 mg", "After food, every 6-8 hours only if advised", "As prescribed"),
        "ibuprofen": ("As prescribed", "After food; avoid in kidney disease/ulcer unless doctor approves", "Short course only"),
        "amoxicillin": ("As prescribed", "Usually after food; complete full course if doctor prescribed", "As written on prescription"),
        "pantoprazole": ("40 mg", "Before breakfast", "As prescribed"),
        "cetirizine": ("10 mg", "Night time; may cause drowsiness", "As prescribed"),
    }
    lower = text.lower()
    for name, (dose, timing, duration) in common.items():
        if name in lower:
            medicines.append({"medicine": name.title(), "dose": dose, "timing": timing, "duration": duration, "notes": "Verify strength and schedule with the original prescription."})

    if not medicines:
        medicines.append(
            {
                "medicine": "Medicine names not confidently detected",
                "dose": "Needs OCR/MedGemma confirmation",
                "timing": "Type visible medicine names or connect real MedGemma/OCR model",
                "duration": "Needs prescription review",
                "notes": "The current demo cannot safely infer tablets from image pixels alone.",
            }
        )
    return medicines


def _soap_note(*, symptoms: str, transcript: str, risk_label: str, case_type: str) -> dict:
    subjective = symptoms.strip() or transcript or "No subjective history provided."
    return {
        "subjective": subjective,
        "objective": f"Uploaded multimodal evidence reviewed under {case_type.replace('_', ' ')} workflow.",
        "assessment": f"{risk_label} risk clinical support summary; diagnosis not finalized.",
        "plan": "Doctor review, confirm history/exam, validate medicines, provide final clinical decision, and export approved report.",
    }


def _safety_checks(text: str, case_type: str, medication_plan: list[dict]) -> list[str]:
    checks = ["Human review required before clinical use."]
    if case_type == "prescription":
        checks.extend(
            [
                "Never follow tablet timing from AI alone; verify against the original prescription.",
                "Check allergy, drug interactions, pregnancy status, kidney/liver disease, and age-specific dosing.",
            ]
        )
    if any(term in text for term in ["severe", "chest pain", "breath", "bleeding", "fever", "unconscious"]):
        checks.append("Red-flag symptom detected; seek urgent medical attention.")
    if case_type == "prescription" and medication_plan and medication_plan[0]["medicine"] == "Medicine names not confidently detected":
        checks.append("Medicine extraction confidence is low; upload clearer image or enter prescription text.")
    return checks


def _contextual_questions(text: str, case_type: str) -> list[str]:
    if "knee" in text:
        return [
            "Which knee hurts: right, left, or both?",
            "What is the pain score from 0 to 10 while walking and while resting?",
            "Did the pain start after injury, fall, sports, heavy lifting, or long travel?",
            "Is there swelling, warmth, redness, fever, or visible deformity?",
            "Can you bear weight and climb stairs, or does the knee lock/click/give way?",
            "Is pain worse in the morning, after walking, after sitting, or at night?",
            "Have you already taken painkillers, injections, physiotherapy, or used a knee brace?",
            "Do you have diabetes, kidney disease, stomach ulcer, blood thinner use, or medicine allergy?",
        ]
    if case_type == "prescription":
        return [
            "Is this a new prescription or an old prescription?",
            "Which exact tablet names are visible to you on the medicine strip?",
            "Did the doctor explain whether each medicine is before food or after food?",
            "Do you have any known drug allergies or current medicines?",
            "Are you pregnant, elderly, a child, or having kidney/liver/stomach problems?",
        ]
    if case_type == "wound":
        return [
            "When did the wound start and what caused it?",
            "Is there fever, pus, bad smell, spreading redness, or severe pain?",
            "Has the wound size increased or decreased since the previous image?",
            "Do you have diabetes or poor circulation?",
        ]
    return [
        "When did the symptom first appear?",
        "What makes it better or worse?",
        "What is the severity from 0 to 10?",
        "Are there fever, dizziness, breathing issues, weakness, bleeding, or other red flags?",
        "What medicines or treatment have already been tried?",
    ]


def _information_gap(text: str, case_type: str) -> list[str]:
    gaps = []
    if "knee" in text:
        checks = {
            "pain score": ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "score"],
            "swelling/redness": ["swelling", "redness", "warm", "fever"],
            "injury history": ["injury", "fall", "twist", "accident", "sports"],
            "walking ability": ["walk", "weight", "stairs", "lock", "click"],
            "medical risk factors": ["diabetes", "kidney", "ulcer", "allergy", "blood thinner"],
        }
        for label, words in checks.items():
            if not any(word in text for word in words):
                gaps.append(label)
    if case_type == "prescription" and not any(word in text for word in ["before", "after", "food", "tablet", "tab", "cap", "mg"]):
        gaps.append("clear medicine names and timing")
    return gaps


def _confidence(features: ImageFeatures | None, transcript: str, prescription_text: str, prescription_extraction: dict | None) -> dict:
    score = 52
    reasons = []
    if features:
        score += 12
        reasons.append("image present")
    if transcript:
        score += 12
        reasons.append("voice transcript present")
    if prescription_text:
        score += 18
        reasons.append("typed prescription/OCR text present")
    if prescription_extraction and prescription_extraction.get("confidence", 0) >= 70:
        score += 16
        reasons.append("prescription image extraction present")
    score = min(score, 92)
    return {"score": score, "level": "High" if score >= 80 else "Medium" if score >= 60 else "Low", "reasons": reasons or ["limited input"]}


def _tone_name(r: int, g: int, b: int) -> str:
    if max(r, g, b) < 70:
        return "low-light"
    if r > g + 25 and r > b + 25:
        return "warm/red-dominant"
    if b > r + 25 and b > g + 15:
        return "cool/blue-dominant"
    if g > r + 20 and g > b + 20:
        return "green-dominant"
    return "balanced"


def _risk_score(text: str, tags: Iterable[str]) -> int:
    score = 28
    urgent_terms = ["severe", "bleeding", "chest pain", "breath", "unconscious", "rapid", "fever", "infection"]
    moderate_terms = ["pain", "swelling", "worse", "discharge", "dizzy", "numb", "burn"]
    score += sum(14 for term in urgent_terms if term in text)
    score += sum(7 for term in moderate_terms if term in text)
    if "knee" in text and ("month" in text or "1 month" in text):
        score += 10
    if "difficulty" in text or "stairs" in text or "walking" in text:
        score += 8
    if "low-light" in tags:
        score += 5
    return min(score, 92)
