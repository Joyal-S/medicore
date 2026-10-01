from decimal import Decimal
from django.test import TestCase, Client
from django.urls import reverse
from Admin.models import tbl_district, tbl_place, tbl_audit_log
from Guest.models import tbl_registration, tbl_shop
from Shop.models import tbl_category, tbl_medicine, tbl_stock
from User.models import tbl_booking, tbl_cart, tbl_notification
from mainproject.security import hash_password


class OrderLifecycleAndWorkflowTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.district = tbl_district.objects.create(district_name="Kannur")
        self.place = tbl_place.objects.create(place_name="Thalassery", district=self.district)

        self.patient = tbl_registration.objects.create(
            registration_name="Kannur Patient",
            registration_email="patient_orders@test.com",
            registration_contact="9876543001",
            registration_address="Beach Road",
            registration_password=hash_password("pw"),
            place=self.place
        )

        self.shop = tbl_shop.objects.create(
            shop_name="Care Meds Thalassery",
            shop_email="shop_orders@test.com",
            shop_contact="9876543002",
            shop_password=hash_password("pw"),
            shop_status=1,
            place=self.place
        )

        self.cat = tbl_category.objects.create(category_name="Vitamins")

        self.med1 = tbl_medicine.objects.create(
            medicine_name="Vitamin D3",
            medicine_details="Bone health",
            medicine_price=Decimal("120.00"),
            shop=self.shop,
            category=self.cat,
            medicine_status=0
        )
        tbl_stock.objects.create(medicine=self.med1, stock_qty=20)

        self.med2 = tbl_medicine.objects.create(
            medicine_name="Zinc Supplement",
            medicine_details="Immunity",
            medicine_price=Decimal("45.50"),
            shop=self.shop,
            category=self.cat,
            medicine_status=0
        )
        tbl_stock.objects.create(medicine=self.med2, stock_qty=15)

    def test_complete_order_lifecycle_and_historical_price_snapshot(self):
        """Order successfully transitions from cart -> checkout -> payment -> packing -> delivery."""
        session = self.client.session
        session['uid'] = self.patient.id
        session['role'] = 'user'
        session.save()

        # Step 1: Add to cart
        self.client.get(reverse('User:Addcart', args=[self.med1.id]))
        self.client.get(reverse('User:Addcart', args=[self.med2.id]))

        booking = tbl_booking.objects.get(user=self.patient, booking_status=0)
        cart1 = tbl_cart.objects.get(booking=booking, medicine=self.med1)
        cart2 = tbl_cart.objects.get(booking=booking, medicine=self.med2)

        # Set quantities: 2 x med1 (240.00) + 3 x med2 (136.50) = 376.50
        self.client.post(reverse('User:cartqty'), {'ALT': cart1.id, 'QTY': 2})
        self.client.post(reverse('User:cartqty'), {'ALT': cart2.id, 'QTY': 3})

        # Step 2: Checkout
        res_checkout = self.client.post(reverse('User:Mycart'))
        self.assertRedirects(res_checkout, reverse('User:payment', args=[booking.id]))

        booking.refresh_from_db()
        self.assertEqual(booking.booking_status, 1)  # Checkout initiated
        self.assertEqual(booking.booking_amount, Decimal("376.50"))

        cart1.refresh_from_db()
        self.assertEqual(cart1.unit_price, Decimal("120.00"))
        self.assertEqual(cart1.cart_status, 1)

        # Change medicine price now in the store to ensure historical price remains snapshotted
        self.med1.medicine_price = Decimal("200.00")
        self.med1.save()

        # Step 3: Complete Payment
        res_pay = self.client.post(reverse('User:payment', args=[booking.id]))
        self.assertRedirects(res_pay, reverse('User:payment_suc'))

        booking.refresh_from_db()
        self.assertEqual(booking.booking_status, 2)  # Paid
        # Booking amount unchanged despite price increase
        self.assertEqual(booking.booking_amount, Decimal("376.50"))

        # Verify stock deducted
        self.assertEqual(self.med1.get_available_stock(), 18)
        self.assertEqual(self.med2.get_available_stock(), 12)

        # Step 4: Shop processes order (Packing 2 -> 3)
        session_shop = self.client.session
        session_shop['sid'] = self.shop.id
        session_shop['role'] = 'shop'
        session_shop.save()

        res_pack = self.client.post(reverse('Shop:packing', args=[booking.id]))
        self.assertRedirects(res_pack, reverse('Shop:booking'))
        booking.refresh_from_db()
        self.assertEqual(booking.booking_status, 3)

        # Step 5: Shop completes delivery (3 -> 4)
        res_del = self.client.post(reverse('Shop:delivery', args=[booking.id]))
        self.assertRedirects(res_del, reverse('Shop:booking'))
        booking.refresh_from_db()
        self.assertEqual(booking.booking_status, 4)

    def test_cannot_pay_order_not_in_status_1(self):
        """Payment endpoint blocks payment if booking status is not 1 (checkout initiated)."""
        session = self.client.session
        session['uid'] = self.patient.id
        session['role'] = 'user'
        session.save()

        # Booking already paid (status 2)
        paid_booking = tbl_booking.objects.create(user=self.patient, booking_amount=Decimal("100.00"), booking_status=2)
        res = self.client.post(reverse('User:payment', args=[paid_booking.id]))
        self.assertRedirects(res, reverse('User:myorder'))
