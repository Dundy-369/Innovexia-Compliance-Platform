from typing import Any

def evaluate_compliance(requirements: dict[str, Any], verified: dict[str, Any]):
    """Simple transparent rule evaluation. Missing data is REVIEW, not an automatic failure."""
    checks=[]
    mapping = {
        "gst_required": ("gst_status", lambda v: str(v or "").upper() == "ACTIVE", "GST registration must be active"),
        "pan_required": ("pan_valid", lambda v: v is True, "PAN must be verified"),
        "udyam_required": ("udyam_valid", lambda v: v is True, "Udyam registration must be verified"),
        "blacklisted": ("blacklisted", lambda v: v is False, "Bidder must not be blacklisted"),
    }
    for req_key,(field,fn,label) in mapping.items():
        if requirements.get(req_key) is True:
            value=verified.get(field)
            status="PASS" if fn(value) else ("REVIEW" if value is None else "FAIL")
            checks.append({"requirement":label,"field":field,"value":value,"status":status})
    if "experience_years" in requirements:
        needed=requirements.get("experience_years")
        actual=verified.get("year_of_experience")
        try:
            status="REVIEW" if actual is None or needed is None else ("PASS" if float(actual)>=float(needed) else "FAIL")
        except (TypeError,ValueError):
            status="REVIEW"
        checks.append({"requirement":f"Minimum experience: {needed} years","field":"year_of_experience","value":actual,"status":status})
    if "minimum_turnover" in requirements:
        needed=requirements.get("minimum_turnover")
        actual=verified.get("turnover")
        try:
            status="REVIEW" if actual is None or needed is None else ("PASS" if float(actual)>=float(needed) else "FAIL")
        except (TypeError,ValueError):
            status="REVIEW"
        checks.append({"requirement":f"Minimum turnover: {needed}","field":"turnover","value":actual,"status":status})
    total=len(checks)
    passed=sum(1 for c in checks if c["status"]=="PASS")
    score=round(100*passed/total) if total else None
    if not checks or any(c["status"]=="REVIEW" for c in checks):
        overall="REVIEW"
    elif any(c["status"]=="FAIL" for c in checks):
        overall="NON_COMPLIANT"
    else:
        overall="COMPLIANT"
    return {"overall":overall,"score":score,"checks":checks,
            "note":"Score is a prototype rule-coverage indicator, not an official GeM score."}
