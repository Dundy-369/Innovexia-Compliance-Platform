from typing import Any
from ..db import get_supabase
from .audit import record_audit

DOC_CONFIG = {
    "PAN": {"ocr_table":"pan_verifications_ocr","ref_table":"pan_reference","ocr_id":"pan_number","ref_id":"pan"},
    "GST": {"ocr_table":"gst_verifications_ocr","ref_table":"gst_reference","ocr_id":"gstin","ref_id":"gstin"},
    "UDYAM": {"ocr_table":"udyam_verifications_ocr","ref_table":"udyam_reference","ocr_id":"udyam_number","ref_id":"udyam_number"},
}

def _first(table: str, column: str, value: str):
    r = get_supabase().table(table).select("*").eq(column, value).limit(1).execute()
    return r.data[0] if r.data else None

def verify_document(document_type: str, bidder_id: str, extracted: dict[str, Any], bid_id: str | None = None):
    kind = document_type.upper()
    if kind not in DOC_CONFIG:
        raise ValueError("document_type must be PAN, GST, or UDYAM")
    cfg = DOC_CONFIG[kind]
    identifier = extracted.get(cfg["ocr_id"])
    if not identifier:
        return {"document_type":kind,"overall":"review","checks":[
            {"label":cfg["ocr_id"],"status":"unreadable","extracted":None,"registered":None}
        ],"message":"Required identifier could not be extracted; manual review is needed."}

    # Find reference record by exact identifier.
    reference = _first(cfg["ref_table"], cfg["ref_id"], identifier)
    checks = []
    checks.append({
        "label":cfg["ocr_id"],
        "status":"match" if reference else "no_record",
        "extracted":identifier,
        "registered":reference.get(cfg["ref_id"]) if reference else None
    })
    org = extracted.get("organization_name")
    if org and reference:
        ref_org = reference.get("company_name") or reference.get("organization_name")
        same = bool(ref_org) and org.strip().casefold() == str(ref_org).strip().casefold()
        checks.append({"label":"organization_name","status":"match" if same else "mismatch",
                       "extracted":org,"registered":ref_org})
    status = "match" if reference and all(c["status"] == "match" for c in checks) else (
        "no_record" if not reference else "review"
    )
    if reference:
        raw_status = (reference.get("status") or reference.get(kind.lower()+"_status") or "").upper()
        if raw_status and raw_status not in ("ACTIVE","VALID","REGISTERED","VERIFIED"):
            checks.append({"label":"registration_status","status":"mismatch","extracted":"submitted document","registered":raw_status})
            status = "mismatch"
    if bid_id:
        record_audit("DOCUMENT_VERIFICATION", bid_id, details={"document_type":kind,"overall":status,"checks":checks})
    return {"document_type":kind,"overall":status,"checks":checks,"reference_found":bool(reference)}

def cross_document_checks(pan: dict | None, gst: dict | None, udyam: dict | None):
    checks=[]
    pan_no=(pan or {}).get("pan_number")
    gst_pan=(gst or {}).get("embedded_pan")
    if pan_no or gst_pan:
        checks.append({"label":"PAN vs GST embedded PAN","status":"match" if pan_no and gst_pan and pan_no.upper()==gst_pan.upper() else "mismatch",
                       "left":pan_no,"right":gst_pan})
    names=[
        ("PAN vs GST organization name",(pan or {}).get("organization_name"),(gst or {}).get("organization_name")),
        ("PAN vs Udyam organization name",(pan or {}).get("organization_name"),(udyam or {}).get("organization_name")),
        ("GST vs Udyam organization name",(gst or {}).get("organization_name"),(udyam or {}).get("organization_name"))
    ]
    for label,a,b in names:
        if a or b:
            checks.append({"label":label,"status":"match" if a and b and a.strip().casefold()==b.strip().casefold() else "mismatch","left":a,"right":b})
    overall="match" if checks and all(c["status"]=="match" for c in checks) else ("review" if not checks else "mismatch")
    return {"overall":overall,"checks":checks}
