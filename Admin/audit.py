"""
Audit logging service for Medicore.
Records administrative and critical business events safely without logging
sensitive medical details, passwords, or personal access tokens.
"""

from typing import Optional
from .models import tbl_audit_log


def log_audit_event(
    action: str,
    actor_type: str,
    actor_name: str,
    details: str,
    actor_id: Optional[int] = None,
    ip_address: Optional[str] = None
) -> tbl_audit_log:
    """
    Records an administrative or lifecycle event in the audit log.
    """
    return tbl_audit_log.objects.create(
        action=action[:100],
        actor_type=actor_type[:50],
        actor_name=actor_name[:100],
        actor_id=actor_id,
        details=details,
        ip_address=ip_address,
    )
