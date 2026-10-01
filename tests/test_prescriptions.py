from decimal import Decimal
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, Client
from django.urls import reverse
from Admin.models import tbl_district, tbl_place
from Guest.models import tbl_registration, tbl_doctor, tbl_shop
from Shop.models import tbl_category, tbl_medicine, tbl_stock
from User.models import tbl_booking, tbl_cart, tbl_request, tbl_prescription, tbl_notification
from mainproject.security import hash_password


class PrescriptionWorkflowAndSecurityTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.district = tbl_district.objects.create(district_name="Alappuzha")
        self.place = tbl_place.objects.create(place_name="Mavelikara", district=self.district)

        self.patient1 = tbl_registration.objects.create(
            registration_name="Rx Patient One",
            registration_email="rx_patient1@test.com",
            registration_contact="9876543501",
            registration_address="Mavelikara",
            registration_password=hash_password("pw"),
            place=self.place
        )

        self.patient2 = tbl_registration.objects.create(
            registration_name="Rx Patient Two",
            registration_email="rx_patient2@test.com",
            registration_contact="9876543502",
            registration_address="Mavelikara",
            registration_password=hash_password("pw"),
            place=self.place
        )

        self.doctor = tbl_doctor.objects.create(
            doctor_name="Dr. Menon",
            doctor_email="menon@test.com",
            doctor_contact="9876543503",
            doctor_password=hash_password("pw"),
            doctor_status=1,
            place=self.place
        )

        self.shop = tbl_shop.objects.create(
            shop_name="Care Pharmacy",
            shop_email="care_rx@test.com",
            shop_contact="9876543504",
            shop_password=hash_password("pw"),
            shop_status=1,
            place=self.place
        )

        self.cat = tbl_category.objects.create(category_name="Antibiotics")

        self.rx_medicine = tbl_medicine.objects.create(
            medicine_name="Azithromycin 500mg",
            medicine_details="Rx Antibiotic",
            medicine_price=Decimal("120.00"),
            shop=self.shop,
            category=self.cat,
            medicine_status=1  # Requires Prescription
        )
        tbl_stock.objects.create(medicine=self.rx_medicine, stock_qty=10)

    def test_doctor_creates_prescription_and_patient_notified(self):
        """Doctor uploads valid PDF prescription; patient receives notification and request status is updated."""
        req = tbl_request.objects.create(
            request_details="Acute bronchitis",
            user=self.patient1,
            dotor=self.doctor,
            request_status=0
        )

        session = self.client.session
        session['did'] = self.doctor.id
        session['role'] = 'doctor'
        session.save()

        pdf_content = b"%PDF-1.4 prescription sample"
        pdf_file = SimpleUploadedFile("rx_menon.pdf", pdf_content, content_type="application/pdf")

        response = self.client.post(reverse('Doctor:prescription', args=[req.id]), {'file': pdf_file})
        self.assertRedirects(response, reverse('Doctor:viewrequest'))

        req.refresh_from_db()
        self.assertEqual(req.request_status, 1)  # Prescribed
        self.assertTrue(tbl_prescription.objects.filter(requestpres=req).exists())

        # Patient notification
        self.assertTrue(tbl_notification.objects.filter(user=self.patient1, notification_type="prescription").exists())

    def test_prescription_required_medicine_flow(self):
        """Prescription medicine requires uploaded prescription before order can be paid."""
        session = self.client.session
        session['uid'] = self.patient1.id
        session['role'] = 'user'
        session.save()

        # Add prescription medicine to cart
        self.client.get(reverse('User:Addcart', args=[self.rx_medicine.id]))

        # Checkout
        res_checkout = self.client.post(reverse('User:Mycart'))
        booking = tbl_booking.objects.get(user=self.patient1, booking_status=1)
        # Redirected to prescription upload, NOT payment
        self.assertRedirects(res_checkout, reverse('User:addprescription', args=[booking.id]))

        # Attempting direct payment without prescription is blocked
        res_pay = self.client.get(reverse('User:payment', args=[booking.id]))
        self.assertRedirects(res_pay, reverse('User:addprescription', args=[booking.id]))

        # Upload valid prescription file
        rx_file = SimpleUploadedFile("doctor_order.png", b"\x89PNG\r\n\x1a\nfakeimage", content_type="image/png")
        res_upload = self.client.post(reverse('User:addprescription', args=[booking.id]), {'prescription': rx_file})
        self.assertRedirects(res_upload, reverse('User:payment', args=[booking.id]))

        booking.refresh_from_db()
        self.assertTrue(bool(booking.prescription))

    def test_oversized_file_upload_rejected(self):
        """Files exceeding max size limit (10MB) are rejected with error."""
        session = self.client.session
        session['uid'] = self.patient1.id
        session['role'] = 'user'
        session.save()

        booking = tbl_booking.objects.create(user=self.patient1, booking_amount=Decimal("120.00"), booking_status=1)

        # 11MB dummy file
        huge_file = SimpleUploadedFile("huge.pdf", b"0" * (11 * 1024 * 1024), content_type="application/pdf")
        res = self.client.post(reverse('User:addprescription', args=[booking.id]), {'prescription': huge_file})
        self.assertEqual(res.status_code, 200)

        booking.refresh_from_db()
        self.assertFalse(bool(booking.prescription))
