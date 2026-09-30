from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db import transaction
from Guest.models import tbl_doctor
from User.models import tbl_request, tbl_prescription
from .models import tbl_disease
from .ml_service import predict_from_symptoms, FRONTEND_SYMPTOMS
from mainproject.security import (
    doctor_required, hash_password, verify_and_upgrade_password, validate_password_strength, validate_uploaded_file
)


@doctor_required
def home(request):
    doctor = get_object_or_404(tbl_doctor, id=request.session["did"])
    pending_count = tbl_request.objects.filter(dotor=doctor, request_status=0).count()
    return render(request, 'Doctor/Home.html', {'doctor': doctor, 'pending_count': pending_count})


@doctor_required
def myprofile(request):
    doctor = get_object_or_404(tbl_doctor, id=request.session["did"])
    return render(request, 'Doctor/MyProfile.html', {'doctor': doctor})


@doctor_required
def editprofile(request):
    doctor = get_object_or_404(tbl_doctor, id=request.session["did"])
    if request.method == 'POST':
        doctor.doctor_name = request.POST.get("name", "").strip()
        doctor.doctor_email = request.POST.get("email", "").strip()
        doctor.doctor_contact = request.POST.get("contact", "").strip()
        doctor.save()
        request.session["name"] = doctor.doctor_name
        messages.success(request, "Profile updated successfully.")
        return redirect("Doctor:editprofile")
    else:
        return render(request, 'Doctor/EditProfile.html', {'doctor': doctor})


@doctor_required
def changepass(request):
    doctor = get_object_or_404(tbl_doctor, id=request.session["did"])
    if request.method == 'POST':
        old = request.POST.get("old", "")
        new = request.POST.get("new", "")
        retype = request.POST.get("ren", "")

        if verify_and_upgrade_password(doctor, 'doctor_password', old):
            if new != retype:
                message = "New passwords do not match."
            else:
                is_valid_pwd, pwd_err = validate_password_strength(new)
                if not is_valid_pwd:
                    message = pwd_err
                else:
                    doctor.doctor_password = hash_password(new)
                    doctor.save(update_fields=['doctor_password'])
                    message = "Password changed successfully!"
        else:
            message = "Old password is incorrect."

        return render(request, 'Doctor/ChangePassword.html', {'doctor': doctor, 'message': message})

    return render(request, 'Doctor/ChangePassword.html', {'doctor': doctor})


@doctor_required
def viewrequest(request):
    """View patient requests specifically assigned to this logged-in doctor."""
    doctor = get_object_or_404(tbl_doctor, id=request.session["did"])
    requestview = tbl_request.objects.filter(dotor=doctor).select_related('user').order_by('-request_date')
    return render(request, 'Doctor/ViewRequest.html', {'requestview': requestview})


@doctor_required
def prescription(request, id):
    """Upload prescription for a request belonging specifically to the logged-in doctor."""
    doctor = get_object_or_404(tbl_doctor, id=request.session["did"])
    req = get_object_or_404(tbl_request, id=id, dotor=doctor)

    if request.method == "POST":
        file = request.FILES.get("file")
        if not file:
            messages.error(request, "Please select a prescription file to upload.")
            return render(request, 'Doctor/Prescription.html', {'request': req})

        is_valid, err = validate_uploaded_file(file, allow_pdf=True, max_size_mb=10)
        if not is_valid:
            messages.error(request, err)
            return render(request, 'Doctor/Prescription.html', {'request': req})

        with transaction.atomic():
            req.request_status = 1
            req.save(update_fields=['request_status'])
            tbl_prescription.objects.create(prescription_file=file, requestpres=req)
        messages.success(request, "Prescription uploaded successfully.")
        return redirect("Doctor:viewrequest")
    else:
        return render(request, 'Doctor/Prescription.html', {'request': req})


@doctor_required
def checkdisease(request, id):
    """
    ML-assisted disease decision support tool for the doctor.
    Enforces doctor ownership of the consultation request.
    """
    doctor = get_object_or_404(tbl_doctor, id=request.session["did"])
    reqid = get_object_or_404(tbl_request, id=id, dotor=doctor)

    if request.method == 'POST':
        psymptoms = request.POST.getlist('symptoms[]', [])
        prediction_result = predict_from_symptoms(psymptoms)

        predicted_disease = prediction_result['predicted_disease']
        confidencescore = prediction_result['confidence_score']
        selected_symptoms_labels = prediction_result['symptoms_selected']

        if predicted_disease:
            symptoms_str = ' '.join(selected_symptoms_labels)
            tbl_disease.objects.create(
                disease_name=predicted_disease,
                disease_symptoms=symptoms_str,
                doctor=doctor,
                reqpre=reqid
            )

        return render(request, 'Doctor/Checkdisease.html', {
            'predicted_disease': predicted_disease,
            'confidence_score': confidencescore,
            'symptoms_selected': selected_symptoms_labels,
            'symptomslist': FRONTEND_SYMPTOMS,
            'disclaimer': prediction_result['disclaimer'],
        })
    else:
        return render(request, 'Doctor/Checkdisease.html', {
            'symptomslist': FRONTEND_SYMPTOMS
        })


def dlogout(request):
    request.session.flush()
    return redirect('Guest:login')