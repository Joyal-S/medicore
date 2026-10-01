from decimal import Decimal
from django.test import TestCase
from django.db import IntegrityError
from Admin.models import tbl_district, tbl_place, tbl_adminregistration, tbl_audit_log
from Guest.models import tbl_registration, tbl_doctor, tbl_shop
from Shop.models import tbl_category, tbl_medicine, tbl_stock
from User.models import tbl_booking, tbl_cart, tbl_request, tbl_prescription, tbl_rating, tbl_notification
from mainproject.security import hash_password


class ModelIntegrityAndConstraintTests(TestCase):
    def setUp(self):
        self.district = tbl_district.objects.create(district_name="Wayanad")
        self.place = tbl_place.objects.create(place_name="Kalpetta", district=self.district)

        self.user = tbl_registration.objects.create(
            registration_name="John Doe",
            registration_email="johndoe@test.com",
            registration_contact="9876543210",
            registration_address="Kalpetta Town",
            registration_password=hash_password("password123"),
            place=self.place
        )

        self.doctor = tbl_doctor.objects.create(
            doctor_name="Dr. Sarah",
            doctor_email="sarah@test.com",
            doctor_contact="9876543211",
            doctor_password=hash_password("docpass123"),
            doctor_status=1,
            place=self.place
        )

        self.shop = tbl_shop.objects.create(
            shop_name="Wayanad Meds",
            shop_email="wayanad@meds.com",
            shop_contact="9876543212",
            shop_password=hash_password("shoppass123"),
            shop_status=1,
            place=self.place
        )

        self.category = tbl_category.objects.create(category_name="Cardiology")

        self.medicine = tbl_medicine.objects.create(
            medicine_name="Atorvastatin 10mg",
            medicine_details="Cholesterol reduction",
            medicine_price=Decimal("85.00"),
            shop=self.shop,
            category=self.category,
            medicine_status=0
        )

    def test_stock_aggregation_method(self):
        """tbl_medicine.get_available_stock accurately aggregates added stock minus paid orders."""
        # Initial stock is 0
        self.assertEqual(self.medicine.get_available_stock(), 0)

        # Add 50 units
        tbl_stock.objects.create(medicine=self.medicine, stock_qty=50)
        self.assertEqual(self.medicine.get_available_stock(), 50)

        # Place paid order for 5 units
        booking = tbl_booking.objects.create(user=self.user, booking_amount=Decimal("425.00"), booking_status=2)
        tbl_cart.objects.create(booking=booking, medicine=self.medicine, cart_quantity=5, cart_status=1)
        self.assertEqual(self.medicine.get_available_stock(), 45)

    def test_cart_unique_booking_medicine_constraint(self):
        """Database constraint prevents multiple rows for the same medicine in a single booking."""
        booking = tbl_booking.objects.create(user=self.user, booking_status=0)
        tbl_cart.objects.create(booking=booking, medicine=self.medicine, cart_quantity=1)
        with self.assertRaises(IntegrityError):
            tbl_cart.objects.create(booking=booking, medicine=self.medicine, cart_quantity=2)

    def test_rating_check_constraint_bounds(self):
        """Database check constraint rejects rating_data values outside 1-5."""
        from django.db import transaction
        with transaction.atomic():
            with self.assertRaises(IntegrityError):
                tbl_rating.objects.create(
                    doctor=self.doctor,
                    user=self.user,
                    user_name="John",
                    rating_data=6
                )
        with transaction.atomic():
            with self.assertRaises(IntegrityError):
                tbl_rating.objects.create(
                    doctor=self.doctor,
                    user=self.user,
                    user_name="John",
                    rating_data=0
                )

    def test_notification_creation_and_defaults(self):
        """Notifications have is_read=False by default and link to recipient."""
        notif = tbl_notification.objects.create(
            user=self.user,
            title="System Alert",
            message="Your appointment is confirmed.",
            notification_type="system"
        )
        self.assertFalse(notif.is_read)
        self.assertEqual(notif.user, self.user)

    def test_audit_log_creation(self):
        """tbl_audit_log records actor details and timestamp."""
        log = tbl_audit_log.objects.create(
            action="PHARMACY_APPROVED",
            actor_type="Admin",
            actor_name="Admin Master",
            actor_id=1,
            details="Approved Wayanad Meds"
        )
        self.assertEqual(log.action, "PHARMACY_APPROVED")
        self.assertIsNotNone(log.created_at)
