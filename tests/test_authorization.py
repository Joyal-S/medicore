from decimal import Decimal
from django.test import TestCase, Client
from django.urls import reverse
from Admin.models import tbl_district, tbl_place, tbl_adminregistration
from Guest.models import tbl_registration, tbl_doctor, tbl_shop
from Shop.models import tbl_category, tbl_medicine, tbl_stock
from User.models import tbl_booking, tbl_cart, tbl_request, tbl_prescription, tbl_complaints, tbl_notification
from mainproject.security import hash_password


class AuthorizationAndIDORTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.district = tbl_district.objects.create(district_name="Thrissur")
        self.place = tbl_place.objects.create(place_name="Guruvayur", district=self.district)

        # Patient 1 and Patient 2
        self.patient1 = tbl_registration.objects.create(
            registration_name="Patient One",
            registration_email="patient1_idor@test.com",
            registration_contact="9876543101",
            registration_address="P1 St",
            registration_password=hash_password("pw1"),
            place=self.place
        )
        self.patient2 = tbl_registration.objects.create(
            registration_name="Patient Two",
            registration_email="patient2_idor@test.com",
            registration_contact="9876543102",
            registration_address="P2 St",
            registration_password=hash_password("pw2"),
            place=self.place
        )

        # Doctor 1 and Doctor 2
        self.doctor1 = tbl_doctor.objects.create(
            doctor_name="Dr. Alpha",
            doctor_email="doc1_idor@test.com",
            doctor_contact="9876543103",
            doctor_password=hash_password("docpw1"),
            doctor_status=1,
            place=self.place
        )
        self.doctor2 = tbl_doctor.objects.create(
            doctor_name="Dr. Beta",
            doctor_email="doc2_idor@test.com",
            doctor_contact="9876543104",
            doctor_password=hash_password("docpw2"),
            doctor_status=1,
            place=self.place
        )

        # Shop 1 and Shop 2
        self.shop1 = tbl_shop.objects.create(
            shop_name="Pharma One",
            shop_email="shop1_idor@test.com",
            shop_contact="9876543105",
            shop_password=hash_password("shoppw1"),
            shop_status=1,
            place=self.place
        )
        self.shop2 = tbl_shop.objects.create(
            shop_name="Pharma Two",
            shop_email="shop2_idor@test.com",
            shop_contact="9876543106",
            shop_password=hash_password("shoppw2"),
            shop_status=1,
            place=self.place
        )

        self.category = tbl_category.objects.create(category_name="Painkiller")

        self.med1 = tbl_medicine.objects.create(
            medicine_name="Pharma1 Med",
            medicine_details="Details",
            medicine_price=Decimal("50.00"),
            shop=self.shop1,
            category=self.category,
            medicine_status=0
        )
        self.med2 = tbl_medicine.objects.create(
            medicine_name="Pharma2 Med",
            medicine_details="Details",
            medicine_price=Decimal("75.00"),
            shop=self.shop2,
            category=self.category,
            medicine_status=0
        )

    def test_patient_cannot_delete_another_patients_cart_item(self):
        """Patient 2 cannot delete Patient 1's cart item (returns 404)."""
        booking = tbl_booking.objects.create(user=self.patient1, booking_status=0)
        cart_item = tbl_cart.objects.create(booking=booking, medicine=self.med1, cart_quantity=1)

        # Log in as Patient 2
        session = self.client.session
        session['uid'] = self.patient2.id
        session['role'] = 'user'
        session.save()

        response = self.client.post(reverse('User:delcart', args=[cart_item.id]))
        self.assertEqual(response.status_code, 404)
        self.assertTrue(tbl_cart.objects.filter(id=cart_item.id).exists())

    def test_patient_cannot_modify_another_patients_cart_quantity(self):
        """Patient 2 cannot alter quantity of Patient 1's cart item (returns 404)."""
        booking = tbl_booking.objects.create(user=self.patient1, booking_status=0)
        cart_item = tbl_cart.objects.create(booking=booking, medicine=self.med1, cart_quantity=1)

        session = self.client.session
        session['uid'] = self.patient2.id
        session['role'] = 'user'
        session.save()

        response = self.client.post(reverse('User:cartqty'), {'ALT': cart_item.id, 'QTY': 5})
        self.assertEqual(response.status_code, 404)
        cart_item.refresh_from_db()
        self.assertEqual(cart_item.cart_quantity, 1)

    def test_doctor_cannot_view_or_diagnose_unassigned_request(self):
        """Doctor 2 cannot access checkdisease or diagnose Doctor 1's consultation request (returns 404)."""
        req = tbl_request.objects.create(
            request_details="Chest congestion",
            user=self.patient1,
            dotor=self.doctor1,
            request_status=0
        )

        session = self.client.session
        session['did'] = self.doctor2.id
        session['role'] = 'doctor'
        session.save()

        response = self.client.get(reverse('Doctor:checkdisease', args=[req.id]))
        self.assertEqual(response.status_code, 404)

    def test_doctor_cannot_upload_prescription_for_unassigned_request(self):
        """Doctor 2 cannot prescribe for Doctor 1's consultation request (returns 404)."""
        req = tbl_request.objects.create(
            request_details="Knee pain",
            user=self.patient1,
            dotor=self.doctor1,
            request_status=0
        )

        session = self.client.session
        session['did'] = self.doctor2.id
        session['role'] = 'doctor'
        session.save()

        response = self.client.get(reverse('Doctor:prescription', args=[req.id]))
        self.assertEqual(response.status_code, 404)

    def test_shop_cannot_modify_or_stock_another_shops_medicine(self):
        """Shop 1 cannot add stock or delete Shop 2's medicine (returns 404)."""
        session = self.client.session
        session['sid'] = self.shop1.id
        session['role'] = 'shop'
        session.save()

        # Delete attempt
        res_del = self.client.post(reverse('Shop:deletemed', args=[self.med2.id]))
        self.assertEqual(res_del.status_code, 404)

        # Add stock attempt
        res_stock = self.client.post(reverse('Shop:addstock', args=[self.med2.id]), {'stock_qty': 100})
        self.assertEqual(res_stock.status_code, 404)

    def test_shop_cannot_change_order_status_for_unrelated_order(self):
        """Shop 1 cannot pack or deliver an order containing items only from Shop 2."""
        booking2 = tbl_booking.objects.create(user=self.patient1, booking_amount=Decimal("75.00"), booking_status=2)
        tbl_cart.objects.create(booking=booking2, medicine=self.med2, cart_quantity=1, cart_status=1, unit_price=Decimal("75.00"))

        session = self.client.session
        session['sid'] = self.shop1.id
        session['role'] = 'shop'
        session.save()

        # Attempt packing
        res_pack = self.client.post(reverse('Shop:packing', args=[booking2.id]))
        self.assertEqual(res_pack.status_code, 404)
        booking2.refresh_from_db()
        self.assertEqual(booking2.booking_status, 2)
