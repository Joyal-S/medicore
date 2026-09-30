from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.db.models import Sum, Count
from django.db import transaction
from django.views.decorators.http import require_POST
from django.contrib import messages
from Guest.models import tbl_registration, tbl_doctor, tbl_shop
from User.models import (
    tbl_complaints, tbl_request, tbl_prescription,
    tbl_booking, tbl_cart, tbl_rating
)
from Shop.models import tbl_category, tbl_medicine, tbl_stock
from mainproject.security import (
    user_required, hash_password, verify_and_upgrade_password, validate_password_strength
)



@user_required
def home(request):
    user = get_object_or_404(tbl_registration, id=request.session["uid"])
    return render(request, 'User/Home.html', {'user': user})


@user_required
def myprofile(request):
    user = get_object_or_404(tbl_registration, id=request.session["uid"])
    return render(request, 'User/MyProfile.html', {'user': user})


@user_required
def editprofile(request):
    user = get_object_or_404(tbl_registration, id=request.session["uid"])
    if request.method == 'POST':
        user.registration_name = request.POST.get("name", "").strip()
        user.registration_email = request.POST.get("email", "").strip()
        user.registration_contact = request.POST.get("contact", "").strip()
        user.registration_address = request.POST.get("address", "").strip()
        user.save()
        request.session["name"] = user.registration_name
        messages.success(request, "Profile updated successfully.")
        return redirect("User:editprofile")
    else:
        return render(request, 'User/EditProfile.html', {'user': user})


@user_required
def changepass(request):
    user = get_object_or_404(tbl_registration, id=request.session["uid"])
    if request.method == 'POST':
        old = request.POST.get("old", "")
        new = request.POST.get("new", "")
        retype = request.POST.get("ren", "")

        if verify_and_upgrade_password(user, 'registration_password', old):
            if new != retype:
                message = "New passwords do not match."
            else:
                is_valid_pwd, pwd_err = validate_password_strength(new)
                if not is_valid_pwd:
                    message = pwd_err
                else:
                    user.registration_password = hash_password(new)
                    user.save(update_fields=['registration_password'])
                    message = "Password changed successfully!"
        else:
            message = "Old password is incorrect."

        return render(request, 'User/ChangePassword.html', {'user': user, 'message': message})

    return render(request, 'User/ChangePassword.html', {'user': user})


@user_required
def complaints(request):
    """View and submit complaints strictly belonging to the logged-in user."""
    user = get_object_or_404(tbl_registration, id=request.session["uid"])
    # IDOR fix: Only fetch complaints filed by THIS user, never all users
    user_complaints = tbl_complaints.objects.filter(user=user).order_by('-complaints_date')

    if request.method == "POST":
        subject = request.POST.get("subject", "").strip()
        content = request.POST.get("complaint", "").strip()
        if subject and content:
            tbl_complaints.objects.create(
                complaints_subject=subject,
                complaints_content=content,
                user=user
            )
            messages.success(request, "Complaint submitted successfully.")
            return redirect("User:complaints")
        else:
            messages.error(request, "Please provide both subject and complaint content.")

    return render(request, "User/Compalints.html", {'complaint': user_complaints, 'user': user})


@user_required
def viewdoctor(request):
    """Browse approved doctors along with their calculated average star ratings."""
    doctors = tbl_doctor.objects.filter(doctor_status=1).select_related('place')
    stars_range = [1, 2, 3, 4, 5]
    avg_ratings = []

    for doc in doctors:
        rating_agg = tbl_rating.objects.filter(doctor=doc).aggregate(
            total=Sum('rating_data'),
            count=Count('id')
        )
        total = rating_agg['total'] or 0
        count = rating_agg['count'] or 0
        avg = round(total / count) if count > 0 else 0
        avg_ratings.append(avg)

    doctor_data = zip(doctors, avg_ratings)
    return render(request, 'User/ViewDoctors.html', {'doctor': doctor_data, 'ar': stars_range})


@user_required
def request(request, id):
    """Submit a consultation request to a specific approved doctor."""
    user = get_object_or_404(tbl_registration, id=request.session["uid"])
    doctor = get_object_or_404(tbl_doctor, id=id, doctor_status=1)

    if request.method == "POST":
        details = request.POST.get("details", "").strip()
        if details:
            tbl_request.objects.create(
                request_details=details,
                user=user,
                dotor=doctor,
                request_status=0
            )
            messages.success(request, f"Consultation request sent to Dr. {doctor.doctor_name}.")
            return redirect("User:viewrequest")
        else:
            messages.error(request, "Please provide request details.")

    return render(request, 'User/Request.html', {'user': user, 'doctor': doctor})


@user_required
def viewrequest(request):
    """View consultation requests filed by the logged-in user."""
    user = get_object_or_404(tbl_registration, id=request.session["uid"])
    requestview = tbl_request.objects.filter(user=user).select_related('dotor').order_by('-request_date')
    return render(request, 'User/ViewRequest.html', {'requestview': requestview})


@user_required
def viewprescription(request, id):
    """View prescription details strictly for requests belonging to the logged-in user."""
    user = get_object_or_404(tbl_registration, id=request.session["uid"])
    requestview = get_object_or_404(tbl_request, id=id, user=user)
    prescription_list = tbl_prescription.objects.filter(requestpres=requestview)

    if not prescription_list.exists():
        messages.info(request, "No prescription has been uploaded for this consultation yet.")
        return redirect("User:viewrequest")

    return render(request, 'User/ViewPrescription.html', {
        'requestview': requestview,
        'prescription': prescription_list
    })


@user_required
def viewshop(request):
    """Browse all approved pharmacies / shops."""
    shops = tbl_shop.objects.filter(shop_status=1).select_related('place')
    return render(request, 'User/ViewShop.html', {'shop': shops})


@user_required
def viewmedicine(request, id):
    """View medicines offered by a specific shop, with optional search filter."""
    shop = get_object_or_404(tbl_shop, id=id, shop_status=1)
    categories = tbl_category.objects.all()
    search_query = request.POST.get("Search", "").strip() if request.method == "POST" else ""

    if search_query:
        medicines = tbl_medicine.objects.filter(shop=shop, medicine_name__icontains=search_query)
    else:
        medicines = tbl_medicine.objects.filter(shop=shop)

    return render(request, 'User/ViewMed.html', {
        'med': medicines,
        'category': categories,
        'shop': shop
    })


@user_required
def Addcart(request, mid):
    """Add medicine to the user's active shopping cart after stock check."""
    medicine = get_object_or_404(tbl_medicine, id=mid)
    user = get_object_or_404(tbl_registration, id=request.session["uid"])

    # Stock validation
    total_stock = tbl_stock.objects.filter(medicine=medicine).aggregate(total=Sum('stock_qty'))['total'] or 0
    total_sold = tbl_cart.objects.filter(
        medicine=medicine,
        cart_status=1,
        booking__booking_status__in=[2, 3, 4]
    ).aggregate(total=Sum('cart_quantity'))['total'] or 0
    available_stock = total_stock - total_sold

    if available_stock <= 0:
        messages.error(request, f"Sorry, '{medicine.medicine_name}' is currently out of stock.")
        return redirect("User:viewmedicine", id=medicine.shop_id)

    # Fetch or create the active cart booking (booking_status=0)
    bookingdata, _ = tbl_booking.objects.get_or_create(user=user, booking_status=0)

    cart_item, created = tbl_cart.objects.get_or_create(
        booking=bookingdata,
        medicine=medicine,
        defaults={'cart_quantity': 1, 'unit_price': medicine.medicine_price}
    )

    if not created:
        messages.info(request, f"'{medicine.medicine_name}' is already in your cart.")
    else:
        messages.success(request, f"Added '{medicine.medicine_name}' to cart.")

    return redirect("User:Mycart")


@user_required
def Mycart(request):
    """
    View cart and handle checkout.
    Calculates prices server-side, validates stock, and handles empty cart safely.
    """
    user = get_object_or_404(tbl_registration, id=request.session["uid"])

    if request.method == "POST":
        bookingdata = tbl_booking.objects.filter(user=user, booking_status=0).first()
        if not bookingdata:
            messages.error(request, "No active cart found.")
            return redirect("User:Mycart")

        cart_items = tbl_cart.objects.filter(booking=bookingdata).select_related('medicine')

        # Empty Cart Bug fix: prevent UnboundLocalError
        if not cart_items.exists():
            messages.error(request, "Your cart is empty. Please add items before checking out.")
            return redirect("User:Mycart")

        # Server-side price calculation and stock validation inside atomic transaction
        with transaction.atomic():
            calculated_total = Decimal("0.00")
            requires_prescription = False

            for item in cart_items:
                # Check current available stock
                total_stock = tbl_stock.objects.filter(medicine=item.medicine).aggregate(total=Sum('stock_qty'))['total'] or 0
                sold_qty = tbl_cart.objects.filter(
                    medicine=item.medicine,
                    cart_status=1,
                    booking__booking_status__in=[2, 3, 4]
                ).aggregate(total=Sum('cart_quantity'))['total'] or 0
                available = total_stock - sold_qty

                if item.cart_quantity > available:
                    messages.error(
                        request,
                        f"Insufficient stock for '{item.medicine.medicine_name}'. "
                        f"Requested: {item.cart_quantity}, Available: {max(available, 0)}."
                    )
                    return redirect("User:Mycart")

                # Snapshot historical unit price
                item.unit_price = item.medicine.medicine_price
                item.cart_status = 1
                item.save()

                line_total = Decimal(item.cart_quantity) * item.medicine.medicine_price
                calculated_total += line_total

                if item.medicine.medicine_status == 1:
                    requires_prescription = True

            bookingdata.booking_amount = calculated_total
            bookingdata.booking_status = 1  # Checkout initiated
            bookingdata.save()

        if requires_prescription:
            return redirect("User:addprescription", id=bookingdata.id)
        else:
            return redirect("User:payment", id=bookingdata.id)

    else:
        bookingdata = tbl_booking.objects.filter(user=user, booking_status=0).first()
        if bookingdata:
            cart = tbl_cart.objects.filter(booking=bookingdata).select_related('medicine')
            for item in cart:
                total_stock = tbl_stock.objects.filter(medicine=item.medicine_id).aggregate(total=Sum('stock_qty'))['total'] or 0
                total_cart = tbl_cart.objects.filter(
                    medicine=item.medicine_id,
                    cart_status=1,
                    booking__booking_status__in=[2, 3, 4]
                ).aggregate(total=Sum('cart_quantity'))['total'] or 0
                item.total_stock = max(0, total_stock - total_cart)
            return render(request, "User/MyCart.html", {'cartdata': cart})
        else:
            return render(request, "User/MyCart.html", {'cartdata': []})


@user_required
def payment(request, id):
    """
    Process order payment. Enforces ownership and validates prescription requirement.
    """
    user = get_object_or_404(tbl_registration, id=request.session["uid"])
    bookingdata = get_object_or_404(tbl_booking, id=id, user=user)

    # Check prescription requirement before allowing payment
    requires_rx = tbl_cart.objects.filter(booking=bookingdata, medicine__medicine_status=1).exists()
    if requires_rx and not bookingdata.prescription:
        messages.error(request, "A doctor's prescription must be uploaded for prescription medicines before payment.")
        return redirect("User:addprescription", id=bookingdata.id)

    if request.method == "POST":
        with transaction.atomic():
            bookingdata.booking_status = 2  # Paid / Placed
            bookingdata.save(update_fields=['booking_status'])
        messages.success(request, "Payment successful! Your order has been placed.")
        return redirect("User:payment_suc")
    else:
        return render(request, 'User/Payment.html', {'total': bookingdata.booking_amount})


@user_required
def payment_suc(request):
    return render(request, "User/Payment_suc.html")


@user_required
@require_POST
def DelCart(request, did):
    """Delete a cart item. Enforces ownership of the item and active booking (POST required)."""
    user = get_object_or_404(tbl_registration, id=request.session["uid"])
    cart_item = get_object_or_404(tbl_cart, id=did, booking__user=user, booking__booking_status=0)
    cart_item.delete()
    messages.success(request, "Item removed from cart.")
    return redirect("User:Mycart")


@user_required
def CartQty(request):
    """Update item quantity in active cart. Enforces ownership and stock bounds."""
    user = get_object_or_404(tbl_registration, id=request.session["uid"])
    raw_qty = request.GET.get('QTY') or request.POST.get('QTY')
    cartid = request.GET.get('ALT') or request.POST.get('ALT')

    if not cartid or not raw_qty:
        return redirect("User:Mycart")

    cartdata = get_object_or_404(tbl_cart, id=cartid, booking__user=user, booking__booking_status=0)

    try:
        qty = int(raw_qty)
        if qty < 1:
            qty = 1
    except ValueError:
        qty = 1

    # Check stock
    total_stock = tbl_stock.objects.filter(medicine=cartdata.medicine).aggregate(total=Sum('stock_qty'))['total'] or 0
    sold_qty = tbl_cart.objects.filter(
        medicine=cartdata.medicine,
        cart_status=1,
        booking__booking_status__in=[2, 3, 4]
    ).aggregate(total=Sum('cart_quantity'))['total'] or 0
    available = max(0, total_stock - sold_qty)

    if qty > available:
        qty = max(1, available)
        messages.warning(request, f"Quantity adjusted to available stock ({available}).")

    cartdata.cart_quantity = qty
    cartdata.save(update_fields=['cart_quantity'])
    return redirect("User:Mycart")


@user_required
def addprescription(request, id):
    """Upload prescription for a booking containing prescription-required medicines."""
    user = get_object_or_404(tbl_registration, id=request.session["uid"])
    bookingdata = get_object_or_404(tbl_booking, id=id, user=user)

    if request.method == "POST":
        prescription_file = request.FILES.get("prescription")
        if not prescription_file:
            messages.error(request, "Please select a valid prescription file to upload.")
            return render(request, 'User/UploadPrescription.html')

        bookingdata.prescription = prescription_file
        bookingdata.save()
        messages.success(request, "Prescription uploaded successfully.")
        return redirect("User:payment", id=bookingdata.id)
    else:
        return render(request, 'User/UploadPrescription.html')


@user_required
def search(request):
    """Global medicine search."""
    categories = tbl_category.objects.all()
    search_query = request.POST.get("Search", "").strip() if request.method == "POST" else ""

    if search_query:
        medicines = tbl_medicine.objects.filter(medicine_name__icontains=search_query)
    else:
        medicines = tbl_medicine.objects.all()

    return render(request, 'User/ViewMed.html', {'med': medicines, 'category': categories})


@user_required
def myorder(request):
    """View past and active orders for the logged-in user."""
    user = get_object_or_404(tbl_registration, id=request.session["uid"])
    orders = tbl_booking.objects.filter(
        user=user,
        booking_status__in=[2, 3, 4]
    ).prefetch_related('tbl_cart_set__medicine').order_by('-booking_date')
    return render(request, 'User/MyOrder.html', {'orders': orders})


@user_required
def rating(request, mid):
    """View doctor ratings and reviews."""
    doctor = get_object_or_404(tbl_doctor, id=mid)
    user = get_object_or_404(tbl_registration, id=request.session["uid"])
    stars_array = [1, 2, 3, 4, 5]

    ratings_qs = tbl_rating.objects.filter(doctor=doctor).order_by('-datetime')
    count = ratings_qs.count()

    if count > 0:
        total = ratings_qs.aggregate(total=Sum('rating_data'))['total'] or 0
        avg = round(total / count)
        return render(request, "User/Rating.html", {
            'mid': mid,
            'doctor': doctor,
            'user': user,
            'data': ratings_qs,
            'ar': stars_array,
            'avg': avg,
            'count': count
        })
    else:
        return render(request, "User/Rating.html", {'mid': mid, 'doctor': doctor, 'user': user})


@user_required
def ajaxstar(request):
    """
    Submit a doctor rating.
    Enforces user authentication, binds to request.user, and validates rating bounds (1-5).
    """
    user = get_object_or_404(tbl_registration, id=request.session["uid"])
    stars_array = [1, 2, 3, 4, 5]

    raw_rating = request.POST.get('rating_data') or request.GET.get('rating_data', 5)
    review_text = (request.POST.get('user_review') or request.GET.get('user_review', '')).strip()
    doctor_id = request.POST.get('pid') or request.GET.get('pid')

    doctor = get_object_or_404(tbl_doctor, id=doctor_id)

    try:
        rating_data = int(raw_rating)
        rating_data = max(1, min(5, rating_data))
    except (ValueError, TypeError):
        rating_data = 5

    # Always associate the authenticated user, ignoring client-supplied user_name
    tbl_rating.objects.create(
        user=user,
        user_name=user.registration_name,
        user_review=review_text,
        rating_data=rating_data,
        doctor=doctor
    )

    ratings_list = tbl_rating.objects.filter(doctor=doctor).order_by('-datetime')
    return render(request, "User/AjaxRating.html", {'data': ratings_list, 'ar': stars_array})


@user_required
def starrating(request):
    """Return JSON statistics for a doctor's ratings."""
    doctor_id = request.GET.get("pdt")
    if not doctor_id:
        return JsonResponse({"error": "Doctor ID required"}, status=400)

    rates = tbl_rating.objects.filter(doctor_id=doctor_id)
    ratecount = rates.count()

    counts = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
    for r in rates:
        val = int(r.rating_data)
        if val in counts:
            counts[val] += 1

    result = {
        "five": counts[5],
        "four": counts[4],
        "three": counts[3],
        "two": counts[2],
        "one": counts[1],
        "total_review": ratecount
    }
    return JsonResponse(result)


def ulogout(request):
    request.session.flush()
    return redirect('Guest:login')