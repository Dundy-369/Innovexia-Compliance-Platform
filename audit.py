from datetime import datetime, timezone
from typing import Any
from ..db import get_supabase

def record_audit(action: str, bid_id: str | None = None, actor_id: str | None = None,
                 actor_role: str | None = None, details: dict[str, Any] | None = None):
    row = {
        "action": action,
        "bid_id": bid_id,
        "actor_id": actor_id,
        "actor_role": actor_role,
        "details": details or {},
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    try:
        get_supabase().table("audit_logs").insert(row).execute()
    except Exception:
        # Audit logging failure is surfaced in application logs by callers if needed.
        raise
    return row
