from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db import transaction
from django.views.decorators.http import require_POST
from Guest.models import tbl_shop
from .models import tbl_category, tbl_medicine, tbl_stock
from User.models import tbl_booking
from mainproject.security import (
    shop_required, hash_password, verify_and_upgrade_password, validate_password_strength
)


@shop_required
def home(request):
    shop = get_object_or_404(tbl_shop, id=request.session["sid"])
    return render(request, 'Shop/Home.html', {'shop': shop})


@shop_required
def myprofile(request):
    shop = get_object_or_404(tbl_shop, id=request.session["sid"])
    return render(request, 'Shop/MyProfile.html', {'shop': shop})


@shop_required
def editprofile(request):
    shop = get_object_or_404(tbl_shop, id=request.session["sid"])
    if request.method == 'POST':
        shop.shop_name = request.POST.get("name", "").strip()
        shop.shop_email = request.POST.get("email", "").strip()
        shop.shop_contact = request.POST.get("contact", "").strip()
        shop.shop_address = request.POST.get("address", "").strip()
        shop.save()
        request.session["name"] = shop.shop_name
        messages.success(request, "Shop profile updated successfully.")
        return redirect("Shop:editprofile")
    else:
        return render(request, 'Shop/EditProfile.html', {'shop': shop})


@shop_required
def changepass(request):
    shop = get_object_or_404(tbl_shop, id=request.session["sid"])
    if request.method == 'POST':
        old = request.POST.get("old", "")
        new = request.POST.get("new", "")
        retype = request.POST.get("ren", "")

        if verify_and_upgrade_password(shop, 'shop_password', old):
            if new != retype:
                message = "New passwords do not match."
            else:
                is_valid_pwd, pwd_err = validate_password_strength(new)
                if not is_valid_pwd:
                    message = pwd_err
                else:
                    shop.shop_password = hash_password(new)
                    shop.save(update_fields=['shop_password'])
                    message = "Password changed successfully!"
        else:
            message = "Old password is incorrect."

        return render(request, 'Shop/ChangePassword.html', {'shop': shop, 'message': message})

    return render(request, 'Shop/ChangePassword.html', {'shop': shop})


@shop_required
def category(request):
    categories = tbl_category.objects.all()
    if request.method == "POST":
        cat_name = request.POST.get("category", "").strip()
        if cat_name:
            tbl_category.objects.create(category_name=cat_name)
            messages.success(request, f"Category '{cat_name}' added successfully.")
        return redirect("Shop:category")
    else:
        return render(request, 'Shop/Category.html', {'category': categories})


@shop_required
def medicine(request):
    shop = get_object_or_404(tbl_shop, id=request.session["sid"])
    medicines = tbl_medicine.objects.filter(shop=shop).select_related('category')
    categories = tbl_category.objects.all()

    if request.method == "POST":
        med_name = request.POST.get("medicine_name", "").strip()
        med_details = request.POST.get("medicine_details", "").strip()
        raw_price = request.POST.get("medicine_price", "0").strip()
        cat_id = request.POST.get("sel_category")
        photo = request.FILES.get("medicine_photo")
        in_stock_radio = request.POST.get("in_stock")

        status = 1 if in_stock_radio == "yes" else 0

        try:
            price = Decimal(raw_price)
            if price <= 0:
                raise ValueError("Price must be greater than zero.")
        except Exception:
            messages.error(request, "Invalid medicine price entered.")
            return render(request, 'Shop/Medicine.html', {'category': categories, 'medicine': medicines})

        category_obj = get_object_or_404(tbl_category, id=cat_id)

        tbl_medicine.objects.create(
            medicine_name=med_name,
            medicine_details=med_details,
            medicine_price=price,
            medicine_photo=photo,
            shop=shop,  # strictly enforce logged-in shop
            category=category_obj,
            medicine_status=status
        )
        messages.success(request, f"Medicine '{med_name}' added successfully.")
        return redirect("Shop:medicine")
    else:
        return render(request, 'Shop/Medicine.html', {'category': categories, 'medicine': medicines})


@shop_required
@require_POST
def deletemed(request, deletemed=None, deletmed=None, **kwargs):
    """Delete a medicine belonging to the logged-in shop (POST strictly required)."""
    med_id = deletemed if deletemed is not None else (deletmed if deletmed is not None else kwargs.get('id'))
    shop = get_object_or_404(tbl_shop, id=request.session["sid"])
    med = get_object_or_404(tbl_medicine, id=med_id, shop=shop)
    med_name = med.medicine_name
    med.delete()
    messages.success(request, f"Medicine '{med_name}' deleted.")
    return redirect("Shop:medicine")

deletmed = deletemed


@shop_required
def addstock(request, mid):
    """Add stock for a medicine belonging to the logged-in shop."""
    shop = get_object_or_404(tbl_shop, id=request.session["sid"])
    med = get_object_or_404(tbl_medicine, id=mid, shop=shop)

    if request.method == "POST":
        raw_qty = request.POST.get("stock_qty", "0").strip()
        try:
            qty = int(raw_qty)
            if qty <= 0:
                raise ValueError()
        except ValueError:
            messages.error(request, "Please enter a valid positive stock quantity.")
            return render(request, 'Shop/AddStock.html', {'medicine': med})

        with transaction.atomic():
            tbl_stock.objects.create(medicine=med, stock_qty=qty)
        messages.success(request, f"Added {qty} units of stock for '{med.medicine_name}'.")
        return redirect("Shop:medicine")
    else:
        return render(request, 'Shop/AddStock.html', {'medicine': med})


@shop_required
def booking(request):
    """View customer orders that contain medicines from the logged-in shop."""
    shop = get_object_or_404(tbl_shop, id=request.session["sid"])
    bookings = tbl_booking.objects.filter(
        booking_status__in=[2, 3, 4],
        tbl_cart__medicine__shop=shop
    ).distinct().select_related('user').prefetch_related('tbl_cart_set__medicine').order_by('-booking_date')
    return render(request, 'Shop/Booking.html', {'booking': bookings})


@shop_required
@require_POST
def packing(request, id):
    """Mark an order status as Packing (status=3). Enforces shop association."""
    shop = get_object_or_404(tbl_shop, id=request.session["sid"])
    booking_obj = get_object_or_404(tbl_booking, id=id, tbl_cart__medicine__shop=shop)
    booking_obj.booking_status = 3
    booking_obj.save(update_fields=['booking_status'])
    messages.success(request, f"Order #{booking_obj.id} marked as Packing.")
    return redirect("Shop:booking")


@shop_required
@require_POST
def delivery(request, id):
    """Mark an order status as Delivered (status=4). Enforces shop association."""
    shop = get_object_or_404(tbl_shop, id=request.session["sid"])
    booking_obj = get_object_or_404(tbl_booking, id=id, tbl_cart__medicine__shop=shop)
    booking_obj.booking_status = 4
    booking_obj.save(update_fields=['booking_status'])
    messages.success(request, f"Order #{booking_obj.id} marked as Delivered.")
    return redirect("Shop:booking")


def slogout(request):
    request.session.flush()
    return redirect('Guest:login')

