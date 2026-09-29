import re
from typing import Any

def extract_fields(document_type: str, text: str) -> dict[str, Any]:
    """Lightweight deterministic parser for prototype OCR text.
    Replace/extend this adapter with the team's OCR output when integrated.
    It does not establish document authenticity.
    """
    t = " ".join((text or "").split())
    out: dict[str, Any] = {"organization_name": None}
    org = re.search(r"(?:company|organization|organisation|legal name|name)\s*[:\-]\s*([A-Za-z0-9 &.,()'-]{3,100})", t, re.I)
    if org:
        out["organization_name"] = org.group(1).strip(" ,.")
    if document_type == "PAN":
        m = re.search(r"\b[A-Z]{5}[0-9]{4}[A-Z]\b", t.upper())
        out["pan_number"] = m.group(0) if m else None
    elif document_type == "GST":
        m = re.search(r"\b[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z]\b", t.upper())
        out["gstin"] = m.group(0) if m else None
        out["embedded_pan"] = out["gstin"][2:12] if out["gstin"] else None
    elif document_type == "UDYAM":
        m = re.search(r"\bUDYAM-[A-Z]{2}-[0-9]{2}-[0-9]{6,8}\b", t.upper())
        out["udyam_number"] = m.group(0) if m else None
    return out

def extract_text_from_file(filename: str, content: bytes) -> tuple[str, str]:
    """Extract text from TXT/PDF where possible. Image OCR is an adapter point.
    If no text is available, caller should mark the document for review.
    """
    suffix = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""
    if suffix in ("txt", "csv"):
        return content.decode("utf-8", errors="ignore"), "text"
    if suffix == "pdf":
        try:
            from pypdf import PdfReader
            import io
            reader = PdfReader(io.BytesIO(content))
            return "\n".join(page.extract_text() or "" for page in reader.pages), "pdf-text"
        except Exception:
            return "", "pdf-unreadable"
    if suffix in ("png", "jpg", "jpeg", "webp"):
        return "", "image-ocr-required"
    return "", "unsupported"
