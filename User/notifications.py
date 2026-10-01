"""
Notification service for Medicore.
Creates and manages workflow notifications across Patients, Doctors, and Pharmacies.
Ensures strict recipient isolation.
"""

from typing import Optional
from .models import tbl_notification
from Guest.models import tbl_registration, tbl_doctor, tbl_shop


def send_notification(
    title: str,
    message: str,
    user: Optional[tbl_registration] = None,
    doctor: Optional[tbl_doctor] = None,
    shop: Optional[tbl_shop] = None,
    notification_type: str = "info"
) -> Optional[tbl_notification]:
    """
    Creates a user, doctor, or shop notification.
    At least one recipient must be supplied.
    """
    if not (user or doctor or shop):
        return None

    return tbl_notification.objects.create(
        user=user,
        doctor=doctor,
        shop=shop,
        title=title[:150],
        message=message,
        notification_type=notification_type,
    )
