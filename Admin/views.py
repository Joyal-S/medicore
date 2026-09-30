from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.contrib import messages
from django.views.decorators.http import require_POST
from .models import tbl_district, tbl_adminregistration, tbl_categary, tbl_place, tbl_scategary
from Guest.models import tbl_registration, tbl_doctor, tbl_shop
from User.models import tbl_complaints
from mainproject.security import (
    admin_required, hash_password, verify_and_upgrade_password, validate_password_strength
)


@admin_required
def district(request):
    districts = tbl_district.objects.all()
    if request.method == "POST":
        dname = request.POST.get("districtInput", "").strip()
        if dname:
            tbl_district.objects.create(district_name=dname)
            messages.success(request, f"District '{dname}' added successfully.")
        return redirect("Admin:district")
    else:
        return render(request, 'Admin/District.html', {'district': districts})


@admin_required
@require_POST
def deletdistrict(request, deletdistrict):
    dis = get_object_or_404(tbl_district, id=deletdistrict)
    dname = dis.district_name
    dis.delete()
    messages.success(request, f"District '{dname}' deleted.")
    return redirect("Admin:district")


@admin_required
def editdistrict(request, editdistrict):
    dis = get_object_or_404(tbl_district, id=editdistrict)
    if request.method == 'POST':
        dname = request.POST.get("districtInput", "").strip()
        if dname:
            dis.district_name = dname
            dis.save()
            messages.success(request, "District updated.")
        return redirect("Admin:district")
    else:
        return render(request, 'Admin/District.html', {'dis': dis})


@admin_required
def registration(request):
    admins = tbl_adminregistration.objects.all()
    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        email = request.POST.get("email", "").strip()
        raw_password = request.POST.get("password", "")
        photo = request.FILES.get("photo")

        if not (name and email and raw_password):
            messages.error(request, "Please fill in all required fields.")
            return render(request, 'Admin/AdminRegistration.html', {'registration': admins})

        is_valid_pwd, pwd_err = validate_password_strength(raw_password)
        if not is_valid_pwd:
            messages.error(request, pwd_err)
            return render(request, 'Admin/AdminRegistration.html', {'registration': admins})

        hashed_password = hash_password(raw_password)
        tbl_adminregistration.objects.create(
            registration_name=name,
            registration_email=email,
            registration_password=hashed_password,
            registration_photo=photo
        )
        messages.success(request, f"Admin account '{name}' created successfully.")
        return redirect("Admin:registration")
    else:
        return render(request, 'Admin/AdminRegistration.html', {'registration': admins})


@admin_required
@require_POST
def deletregister(request, deletregister):
    admin = get_object_or_404(tbl_adminregistration, id=deletregister)
    admin.delete()
    messages.success(request, "Admin removed.")
    return redirect("Admin:registration")


@admin_required
def editregister(request, editregister):
    admin = get_object_or_404(tbl_adminregistration, id=editregister)
    if request.method == 'POST':
        admin.registration_name = request.POST.get("name", "").strip()
        admin.registration_email = request.POST.get("email", "").strip()
        raw_pwd = request.POST.get("password", "")
        if raw_pwd and not raw_pwd.startswith('pbkdf2_'):
            is_valid_pwd, pwd_err = validate_password_strength(raw_pwd)
            if not is_valid_pwd:
                messages.error(request, pwd_err)
                return render(request, 'Admin/AdminRegistration.html', {'dis': admin})
            admin.registration_password = hash_password(raw_pwd)
        admin.save()
        messages.success(request, "Admin account updated.")
        return redirect("Admin:registration")
    else:
        return render(request, 'Admin/AdminRegistration.html', {'dis': admin})


@admin_required
def categary(request):
    categories = tbl_categary.objects.all()
    if request.method == "POST":
        cname = request.POST.get("Input", "").strip()
        if cname:
            tbl_categary.objects.create(categary_name=cname)
            messages.success(request, f"Category '{cname}' created.")
        return redirect("Admin:categary")
    else:
        return render(request, 'Admin/Categary.html', {'categary': categories})


@admin_required
@require_POST
def deletcategary(request, deletcategary):
    cat = get_object_or_404(tbl_categary, id=deletcategary)
    cat.delete()
    messages.success(request, "Category deleted.")
    return redirect("Admin:categary")


@admin_required
def editcategary(request, editcategary):
    cat = get_object_or_404(tbl_categary, id=editcategary)
    if request.method == 'POST':
        cname = request.POST.get("Input", "").strip()
        if cname:
            cat.categary_name = cname
            cat.save()
            messages.success(request, "Category updated.")
        return redirect("Admin:categary")
    else:
        return render(request, 'Admin/Categary.html', {'dis': cat})


@admin_required
def place(request):
    districts = tbl_district.objects.all()
    places = tbl_place.objects.all().select_related('district')
    if request.method == "POST":
        district_id = request.POST.get("sel_district")
        pname = request.POST.get("place", "").strip()
        district_obj = get_object_or_404(tbl_district, id=district_id)
        if pname:
            tbl_place.objects.create(place_name=pname, district=district_obj)
            messages.success(request, f"Place '{pname}' added.")
        return redirect("Admin:place")
    else:
        return render(request, 'Admin/Place.html', {'district': districts, 'place': places})


@admin_required
@require_POST
def deletplace(request, deletplace):
    pl = get_object_or_404(tbl_place, id=deletplace)
    pl.delete()
    messages.success(request, "Place deleted.")
    return redirect("Admin:place")


@admin_required
def editplace(request, editplace):
    pl = get_object_or_404(tbl_place, id=editplace)
    districts = tbl_district.objects.all()
    if request.method == "POST":
        pl.place_name = request.POST.get("place", "").strip()
        district_id = request.POST.get("sel_district")
        pl.district = get_object_or_404(tbl_district, id=district_id)
        pl.save()
        messages.success(request, "Place updated.")
        return redirect("Admin:place")
    else:
        return render(request, 'Admin/Place.html', {'editplace': pl, 'district': districts})


@admin_required
def scategary(request):
    categories = tbl_categary.objects.all()
    subcategories = tbl_scategary.objects.all().select_related('categary')
    if request.method == "POST":
        categary_id = request.POST.get("sel_categary")
        sname = request.POST.get("name", "").strip()
        categary_obj = get_object_or_404(tbl_categary, id=categary_id)
        if sname:
            tbl_scategary.objects.create(scategary_name=sname, categary=categary_obj)
            messages.success(request, f"Subcategory '{sname}' added.")
        return redirect("Admin:scategary")
    else:
        return render(request, 'Admin/Subcategary.html', {'categary': categories, 'scategary': subcategories})


@admin_required
@require_POST
def deletsub(request, deletsub):
    sub = get_object_or_404(tbl_scategary, id=deletsub)
    sub.delete()
    messages.success(request, "Subcategory deleted.")
    return redirect("Admin:scategary")


@admin_required
def edisubcategary(request, edisubcategary):
    sub = get_object_or_404(tbl_scategary, id=edisubcategary)
    categories = tbl_categary.objects.all()
    if request.method == "POST":
        sub.scategary_name = request.POST.get("name", "").strip()
        categary_id = request.POST.get("sel_categary")
        sub.categary = get_object_or_404(tbl_categary, id=categary_id)
        sub.save()
        messages.success(request, "Subcategory updated.")
        return redirect("Admin:scategary")
    else:
        return render(request, 'Admin/Subcategary.html', {'dis': sub, 'categary': categories})


@admin_required
def home(request):
    stats = {
        'user_count': tbl_registration.objects.count(),
        'doctor_count': tbl_doctor.objects.count(),
        'shop_count': tbl_shop.objects.count(),
        'pending_complaints': tbl_complaints.objects.filter(complaints_status=0).count(),
        'pending_doctors': tbl_doctor.objects.filter(doctor_status=0).count(),
        'pending_shops': tbl_shop.objects.filter(shop_status=0).count(),
    }
    return render(request, 'Admin/Home.html', {'stats': stats})


@admin_required
def userlist(request):
    users = tbl_registration.objects.all().select_related('place', 'place__district')
    return render(request, 'Admin/UserList.html', {'user': users})


@admin_required
def shoplist(request):
    pending_shops = tbl_shop.objects.filter(shop_status=0).select_related('place')
    accepted_shops = tbl_shop.objects.filter(shop_status=1).select_related('place')
    rejected_shops = tbl_shop.objects.filter(shop_status=2).select_related('place')
    return render(request, 'Admin/ShopList.html', {
        'shop': pending_shops,
        'accept': accepted_shops,
        'reject': rejected_shops
    })


@admin_required
@require_POST
def accept(request, id):
    shop = get_object_or_404(tbl_shop, id=id)
    shop.shop_status = 1
    shop.save(update_fields=['shop_status'])
    messages.success(request, f"Shop '{shop.shop_name}' approved.")
    return redirect("Admin:shoplist")


@admin_required
@require_POST
def reject(request, id):
    shop = get_object_or_404(tbl_shop, id=id)
    shop.shop_status = 2
    shop.save(update_fields=['shop_status'])
    messages.warning(request, f"Shop '{shop.shop_name}' rejected.")
    return redirect("Admin:shoplist")


@admin_required
def doctorlist(request):
    pending_doctors = tbl_doctor.objects.filter(doctor_status=0).select_related('place')
    accepted_doctors = tbl_doctor.objects.filter(doctor_status=1).select_related('place')
    rejected_doctors = tbl_doctor.objects.filter(doctor_status=2).select_related('place')
    return render(request, 'Admin/DoctorList.html', {
        'doctor': pending_doctors,
        'acceptd': accepted_doctors,
        'rejectd': rejected_doctors
    })


@admin_required
@require_POST
def acceptd(request, id):
    doctor = get_object_or_404(tbl_doctor, id=id)
    doctor.doctor_status = 1
    doctor.save(update_fields=['doctor_status'])
    messages.success(request, f"Dr. {doctor.doctor_name} approved.")
    return redirect("Admin:doctorlist")


@admin_required
@require_POST
def rejectd(request, id):
    doctor = get_object_or_404(tbl_doctor, id=id)
    doctor.doctor_status = 2
    doctor.save(update_fields=['doctor_status'])
    messages.warning(request, f"Dr. {doctor.doctor_name} rejected.")
    return redirect("Admin:doctorlist")


@admin_required
def usercomplaint(request):
    pending_complaints = tbl_complaints.objects.filter(complaints_status=0).select_related('user')
    replied_complaints = tbl_complaints.objects.filter(complaints_status=1).select_related('user')
    return render(request, 'Admin/ViewComplaints.html', {
        'complaint': pending_complaints,
        'user': replied_complaints
    })


@admin_required
def replaycomplaint(request, id):
    complaint = get_object_or_404(tbl_complaints, id=id)
    if request.method == "POST":
        reply_text = request.POST.get("txtreplay", "").strip()
        if reply_text:
            complaint.complaints_reply = reply_text
            complaint.complaints_status = 1
            complaint.complaints_reply_date = timezone.now()
            complaint.save()
            messages.success(request, "Reply sent successfully.")
        return redirect("Admin:usercomplaint")
    else:
        return render(request, 'Admin/Replay.html', {'complaint': complaint})


@admin_required
def myprofile(request):
    admin = get_object_or_404(tbl_adminregistration, id=request.session["aid"])
    return render(request, 'Admin/MyProfile.html', {'admin': admin})


@admin_required
def editprofile(request):
    admin = get_object_or_404(tbl_adminregistration, id=request.session["aid"])
    if request.method == 'POST':
        admin.registration_name = request.POST.get("name", "").strip()
        admin.registration_email = request.POST.get("email", "").strip()
        admin.save()
        request.session["name"] = admin.registration_name
        messages.success(request, "Admin profile updated.")
        return redirect("Admin:myprofile")
    else:
        return render(request, 'Admin/EditProfile.html', {'admin': admin})


@admin_required
def changepass(request):
    admin = get_object_or_404(tbl_adminregistration, id=request.session["aid"])
    if request.method == 'POST':
        old = request.POST.get("old", "")
        new = request.POST.get("new", "")
        retype = request.POST.get("ren", "")

        if verify_and_upgrade_password(admin, 'registration_password', old):
            if new != retype:
                message = "New passwords do not match."
            else:
                is_valid_pwd, pwd_err = validate_password_strength(new)
                if not is_valid_pwd:
                    message = pwd_err
                else:
                    admin.registration_password = hash_password(new)
                    admin.save(update_fields=['registration_password'])
                    message = "Password changed successfully!"
        else:
            message = "Old password is incorrect."

        return render(request, 'Admin/ChangePassword.html', {'admin': admin, 'message': message})

    return render(request, 'Admin/ChangePassword.html', {'admin': admin})


def alogout(request):
    request.session.flush()
    return redirect('Guest:login')