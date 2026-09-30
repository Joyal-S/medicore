from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from Admin.models import tbl_district, tbl_place, tbl_adminregistration
from .models import tbl_registration, tbl_doctor, tbl_shop
from mainproject.security import hash_password, verify_and_upgrade_password, validate_password_strength


def login(request):
    """
    Unified secure login for Admin, Patient, Doctor, and Shop roles.
    Uses Django password hashing with automatic transparent upgrade for legacy accounts.
    """
    if request.method == "POST":
        email = request.POST.get("email", "").strip()
        password = request.POST.get("password", "")

        if not email or not password:
            return render(request, "Guest/Login.html", {'msg': 'Please provide both email and password.'})

        # 1. Check Admin
        admin = tbl_adminregistration.objects.filter(registration_email=email).first()
        if admin and verify_and_upgrade_password(admin, 'registration_password', password):
            request.session.flush()
            request.session["aid"] = admin.id
            request.session["role"] = "admin"
            request.session["name"] = admin.registration_name
            return redirect("Admin:home")

        # 2. Check Patient / User
        user = tbl_registration.objects.filter(registration_email=email).first()
        if user and verify_and_upgrade_password(user, 'registration_password', password):
            request.session.flush()
            request.session["uid"] = user.id
            request.session["role"] = "user"
            request.session["name"] = user.registration_name
            return redirect("User:home")

        # 3. Check Shop
        shop = tbl_shop.objects.filter(shop_email=email).first()
        if shop and verify_and_upgrade_password(shop, 'shop_password', password):
            if shop.shop_status == 0:
                return render(request, "Guest/Login.html", {'msg': 'Your shop account is pending administrator approval.'})
            elif shop.shop_status == 2:
                return render(request, "Guest/Login.html", {'msg': 'Your shop registration was rejected by the administrator.'})
            request.session.flush()
            request.session["sid"] = shop.id
            request.session["role"] = "shop"
            request.session["name"] = shop.shop_name
            return redirect("Shop:home")

        # 4. Check Doctor
        doctor = tbl_doctor.objects.filter(doctor_email=email).first()
        if doctor and verify_and_upgrade_password(doctor, 'doctor_password', password):
            if doctor.doctor_status == 0:
                return render(request, "Guest/Login.html", {'msg': 'Your doctor account is pending administrator approval.'})
            elif doctor.doctor_status == 2:
                return render(request, "Guest/Login.html", {'msg': 'Your doctor registration was rejected by the administrator.'})
            request.session.flush()
            request.session["did"] = doctor.id
            request.session["role"] = "doctor"
            request.session["name"] = doctor.doctor_name
            return redirect("Doctor:home")

        return render(request, "Guest/Login.html", {'msg': 'Invalid email or password.'})
    else:
        return render(request, 'Guest/Login.html')


def registration(request):
    """Register a new patient/user account with secure password hashing."""
    districts = tbl_district.objects.all()
    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        email = request.POST.get("email", "").strip().lower()
        contact = request.POST.get("contact", "").strip()
        address = request.POST.get("address", "").strip()
        place_id = request.POST.get("place")
        photo = request.FILES.get("photo")
        raw_password = request.POST.get("password", "")

        if not (name and email and raw_password and place_id):
            messages.error(request, "Please fill in all required fields.")
            return render(request, 'Guest/UserRegistration.html', {'district': districts})

        if tbl_registration.objects.filter(registration_email=email).exists():
            messages.error(request, "An account with this email address already exists.")
            return render(request, 'Guest/UserRegistration.html', {'district': districts})

        is_valid_pwd, pwd_err = validate_password_strength(raw_password)
        if not is_valid_pwd:
            messages.error(request, pwd_err)
            return render(request, 'Guest/UserRegistration.html', {'district': districts})

        place = get_object_or_404(tbl_place, id=place_id)
        hashed_password = hash_password(raw_password)

        tbl_registration.objects.create(
            registration_name=name,
            registration_email=email,
            registration_contact=contact,
            registration_address=address,
            registration_photo=photo,
            registration_password=hashed_password,
            place=place
        )
        messages.success(request, "Registration successful! You may now log in.")
        return redirect("Guest:login")
    else:
        return render(request, 'Guest/UserRegistration.html', {'district': districts})


def ajaxplace(request):
    """Return place dropdown options for selected district."""
    did = request.GET.get("did")
    if not did:
        return render(request, "Guest/AjaxPlace.html", {'place': []})
    district = get_object_or_404(tbl_district, id=did)
    places = tbl_place.objects.filter(district=district)
    return render(request, "Guest/AjaxPlace.html", {'place': places})


def doctor(request):
    """Register a new doctor (requires admin approval before login)."""
    districts = tbl_district.objects.all()
    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        email = request.POST.get("email", "").strip().lower()
        contact = request.POST.get("contact", "").strip()
        photo = request.FILES.get("photo")
        license_file = request.FILES.get("license")
        place_id = request.POST.get("place")
        raw_password = request.POST.get("password", "")

        if not (name and email and raw_password and place_id and license_file):
            messages.error(request, "Please fill in all required fields including license.")
            return render(request, 'Guest/Doctor.html', {'district': districts})

        if tbl_doctor.objects.filter(doctor_email=email).exists():
            messages.error(request, "A doctor with this email is already registered.")
            return render(request, 'Guest/Doctor.html', {'district': districts})

        is_valid_pwd, pwd_err = validate_password_strength(raw_password)
        if not is_valid_pwd:
            messages.error(request, pwd_err)
            return render(request, 'Guest/Doctor.html', {'district': districts})

        place = get_object_or_404(tbl_place, id=place_id)
        hashed_password = hash_password(raw_password)

        tbl_doctor.objects.create(
            doctor_name=name,
            doctor_email=email,
            doctor_contact=contact,
            doctor_photo=photo,
            doctor_licese=license_file,
            doctor_password=hashed_password,
            place=place,
            doctor_status=0  # Pending approval
        )
        messages.success(request, "Registration submitted! Your account is pending administrator verification.")
        return redirect("Guest:login")
    else:
        return render(request, 'Guest/Doctor.html', {'district': districts})


def shop(request):
    """Register a new pharmacy / shop (requires admin approval before login)."""
    districts = tbl_district.objects.all()
    if request.method == "POST":
        name = request.POST.get("shop_name", "").strip()
        email = request.POST.get("email", "").strip().lower()
        contact = request.POST.get("contact", "").strip()
        address = request.POST.get("address", "").strip()
        photo = request.FILES.get("photo")
        license_file = request.FILES.get("license")
        place_id = request.POST.get("place")
        raw_password = request.POST.get("password", "")

        if not (name and email and raw_password and place_id and license_file):
            messages.error(request, "Please fill in all required fields including pharmacy license.")
            return render(request, 'Guest/Shop.html', {'district': districts})

        if tbl_shop.objects.filter(shop_email=email).exists():
            messages.error(request, "A pharmacy with this email is already registered.")
            return render(request, 'Guest/Shop.html', {'district': districts})

        is_valid_pwd, pwd_err = validate_password_strength(raw_password)
        if not is_valid_pwd:
            messages.error(request, pwd_err)
            return render(request, 'Guest/Shop.html', {'district': districts})

        place = get_object_or_404(tbl_place, id=place_id)
        hashed_password = hash_password(raw_password)

        tbl_shop.objects.create(
            shop_name=name,
            shop_email=email,
            shop_contact=contact,
            shop_address=address,
            shop_photo=photo,
            shop_licese=license_file,
            shop_password=hashed_password,
            place=place,
            shop_status=0  # Pending approval
        )
        messages.success(request, "Shop registered! Your account is pending administrator verification.")
        return redirect("Guest:login")
    else:
        return render(request, 'Guest/Shop.html', {'district': districts})


def index(request):
    return render(request, 'Guest/index.html')