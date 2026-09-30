"""
Security, Authentication, and Authorization helpers for PAWCARE.
Includes password hashing with transparent legacy migration and role-based access decorators.
"""

from functools import wraps
from django.shortcuts import redirect
from django.contrib.auth.hashers import make_password, check_password
from django.contrib import messages
from django.http import HttpResponseForbidden

def hash_password(raw_password):
    """Securely hash a raw password using Django's default hasher."""
    if not raw_password:
        return ""
    return make_password(raw_password)

def verify_and_upgrade_password(instance, password_attr, raw_password):
    """
    Verify password against stored value.
    If the stored value is plaintext, verify and automatically upgrade to a hashed password.
    Returns True if valid, False otherwise.
    """
    if not raw_password or not instance:
        return False
    
    stored = getattr(instance, password_attr, None)
    if not stored:
        return False

    # Check using Django's hasher
    try:
        if check_password(raw_password, stored):
            return True
    except Exception:
        pass

    # Legacy plaintext check
    if raw_password == stored:
        # Upgrade to hashed password immediately
        setattr(instance, password_attr, make_password(raw_password))
        instance.save(update_fields=[password_attr])
        return True

    return False


def admin_required(view_func):
    """Ensure user is logged in as an Admin."""
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        aid = request.session.get("aid")
        if not aid:
            messages.error(request, "Please log in as an administrator to access this page.")
            return redirect("Guest:login")
        from Admin.models import tbl_adminregistration
        if not tbl_adminregistration.objects.filter(id=aid).exists():
            request.session.flush()
            messages.error(request, "Admin account not found. Please log in again.")
            return redirect("Guest:login")
        return view_func(request, *args, **kwargs)
    return _wrapped


def user_required(view_func):
    """Ensure user is logged in as a registered Patient / User."""
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        uid = request.session.get("uid")
        if not uid:
            messages.error(request, "Please log in to access this page.")
            return redirect("Guest:login")
        from Guest.models import tbl_registration
        if not tbl_registration.objects.filter(id=uid).exists():
            request.session.flush()
            messages.error(request, "User account not found. Please log in again.")
            return redirect("Guest:login")
        return view_func(request, *args, **kwargs)
    return _wrapped


def doctor_required(view_func):
    """Ensure user is logged in as an approved Doctor."""
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        did = request.session.get("did")
        if not did:
            messages.error(request, "Please log in as a doctor to access this page.")
            return redirect("Guest:login")
        from Guest.models import tbl_doctor
        doctor = tbl_doctor.objects.filter(id=did).first()
        if not doctor:
            request.session.flush()
            messages.error(request, "Doctor account not found. Please log in again.")
            return redirect("Guest:login")
        if doctor.doctor_status != 1:
            messages.error(request, "Your doctor account is pending administrator approval.")
            return redirect("Guest:login")
        return view_func(request, *args, **kwargs)
    return _wrapped


def shop_required(view_func):
    """Ensure user is logged in as an approved Shop."""
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        sid = request.session.get("sid")
        if not sid:
            messages.error(request, "Please log in as a shop to access this page.")
            return redirect("Guest:login")
        from Guest.models import tbl_shop
        shop = tbl_shop.objects.filter(id=sid).first()
        if not shop:
            request.session.flush()
            messages.error(request, "Shop account not found. Please log in again.")
            return redirect("Guest:login")
        if shop.shop_status != 1:
            messages.error(request, "Your shop account is pending administrator approval.")
            return redirect("Guest:login")
        return view_func(request, *args, **kwargs)
    return _wrapped
