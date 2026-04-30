from __future__ import annotations

from datetime import datetime
from io import BytesIO
from textwrap import wrap


def build_case_pdf(case: dict) -> bytes:
    """Small dependency-free PDF writer for downloadable demo reports."""
    medication_plan = case["analysis"].get("medication_plan", [])
    lines = [
        "VisionFusion MedAI - Multimodal Healthcare Insight Report",
        f"Case ID: {case['id']}",
        f"Patient: {case['patient_name']}",
        f"Workflow: {case.get('case_type', 'general')}",
        f"Role Mode: {case['mode'].title()}",
        f"Model Option: {case['analysis'].get('model_profile', {}).get('label', case.get('model_profile', 'Demo hybrid adapter'))}",
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
        f"Risk Level: {case['analysis']['risk_label']} ({case['analysis']['risk_score']}/100)",
        f"Confidence: {case['analysis'].get('confidence', {}).get('level', 'N/A')} ({case['analysis'].get('confidence', {}).get('score', 'N/A')}/100)",
        "",
        "Summary:",
        case["analysis"]["explanation"],
        "",
        "Clinical Impression:",
        case["analysis"].get("clinical_impression", "Not available"),
        "",
        "Image Interpretation:",
        case["analysis"].get("image_interpretation", "Not available"),
        "",
        "Prescription Image Extraction:",
        case["analysis"].get("prescription_extraction", {}).get("raw_text", "Not available"),
        *[
            f"- Investigation: {item}"
            for item in case["analysis"].get("prescription_extraction", {}).get("investigations", [])
        ],
        "",
        "Missing Information Before Final Guidance:",
        *[f"- {item}" for item in case["analysis"].get("information_gap", [])],
        "",
        "Medication / Prescription Guidance:",
        *[
            f"- {item.get('medicine')}: {item.get('dose')} | {item.get('timing')} | {item.get('duration')} | {item.get('notes')}"
            for item in medication_plan
        ],
        "",
        "SOAP Note:",
        f"S: {case['analysis'].get('soap_note', {}).get('subjective', '')}",
        f"O: {case['analysis'].get('soap_note', {}).get('objective', '')}",
        f"A: {case['analysis'].get('soap_note', {}).get('assessment', '')}",
        f"P: {case['analysis'].get('soap_note', {}).get('plan', '')}",
        "",
        "Observations:",
        *[f"- {item}" for item in case["analysis"]["observations"]],
        "",
        "Safety Checks:",
        *[f"- {item}" for item in case["analysis"].get("safety_checks", [])],
        "",
        "Recommended Next Steps:",
        *[f"- {item}" for item in case["analysis"]["next_steps"]],
        "",
        "Follow-up Questions:",
        *[f"- {item}" for item in case["analysis"]["follow_up_questions"]],
        "",
        "Audit Trail:",
        *[f"- {item}" for item in case.get("audit", [])],
        "",
        "Safety Notice: This report is for clinical decision support and patient education only. It is not a diagnosis and must be reviewed by a qualified healthcare professional.",
    ]
    return _simple_pdf(lines)


def _simple_pdf(lines: list[str]) -> bytes:
    content = ["BT", "/F1 11 Tf", "50 790 Td", "14 TL"]
    first = True
    for raw in lines:
        wrapped = wrap(raw, width=92) or [""]
        for line in wrapped:
            safe = line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
            if first:
                content.append(f"({safe}) Tj")
                first = False
            else:
                content.append("T*")
                content.append(f"({safe}) Tj")
    content.append("ET")
    stream = "\n".join(content).encode("latin-1", "replace")

    objects = []
    objects.append(b"<< /Type /Catalog /Pages 2 0 R >>")
    objects.append(b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>")
    objects.append(b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 842] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>")
    objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    objects.append(b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream")

    output = BytesIO()
    output.write(b"%PDF-1.4\n")
    offsets = [0]
    for index, obj in enumerate(objects, start=1):
        offsets.append(output.tell())
        output.write(f"{index} 0 obj\n".encode())
        output.write(obj)
        output.write(b"\nendobj\n")
    xref = output.tell()
    output.write(f"xref\n0 {len(objects)+1}\n".encode())
    output.write(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        output.write(f"{offset:010d} 00000 n \n".encode())
    output.write(f"trailer << /Size {len(objects)+1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF".encode())
    return output.getvalue()
