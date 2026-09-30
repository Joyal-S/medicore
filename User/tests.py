from decimal import Decimal
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, Client
from django.urls import reverse
from Admin.models import tbl_district, tbl_place
from Guest.models import tbl_registration, tbl_doctor, tbl_shop
from Shop.models import tbl_category, tbl_medicine, tbl_stock
from User.models import tbl_booking, tbl_cart, tbl_complaints, tbl_rating, tbl_request, tbl_prescription
from mainproject.security import hash_password


class UserOrderAndSecurityTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.district = tbl_district.objects.create(district_name="Alappuzha")
        self.place = tbl_place.objects.create(place_name="Cherthala", district=self.district)

        # Users
        self.patient1 = tbl_registration.objects.create(
            registration_name="Patient One",
            registration_email="patient1@test.com",
            registration_contact="1234567890",
            registration_address="Addr 1",
            registration_password=hash_password("pass1"),
            place=self.place
        )
        self.patient2 = tbl_registration.objects.create(
            registration_name="Patient Two",
            registration_email="patient2@test.com",
            registration_contact="1234567891",
            registration_address="Addr 2",
            registration_password=hash_password("pass2"),
            place=self.place
        )

        # Doctor
        self.doctor = tbl_doctor.objects.create(
            doctor_name="Dr. Smith",
            doctor_email="smith@test.com",
            doctor_contact="9876543210",
            doctor_password=hash_password("docpass"),
            doctor_status=1,
            place=self.place
        )

        # Shop
        self.shop = tbl_shop.objects.create(
            shop_name="City Pharmacy",
            shop_email="city@test.com",
            shop_contact="9876543211",
            shop_password=hash_password("shoppass"),
            shop_status=1,
            place=self.place
        )
        self.category = tbl_category.objects.create(category_name="General")

        # Medicines
        # OTC medicine with 10 stock
        self.otc_med = tbl_medicine.objects.create(
            medicine_name="Vitamin C",
            medicine_details="Supplements",
            medicine_price=Decimal("20.00"),
            shop=self.shop,
            category=self.category,
            medicine_status=0  # OTC
        )
        tbl_stock.objects.create(medicine=self.otc_med, stock_qty=10)

        # Prescription-only medicine with 5 stock
        self.rx_med = tbl_medicine.objects.create(
            medicine_name="Antibiotic X",
            medicine_details="Strong Antibiotic",
            medicine_price=Decimal("150.00"),
            shop=self.shop,
            category=self.category,
            medicine_status=1  # Requires Prescription
        )
        tbl_stock.objects.create(medicine=self.rx_med, stock_qty=5)

    def test_patient_cannot_view_another_patients_complaints(self):
        """User only sees their own complaints."""
        tbl_complaints.objects.create(
            complaints_subject="Private complaint 1",
            complaints_content="Content 1",
            user=self.patient1
        )
        comp2 = tbl_complaints.objects.create(
            complaints_subject="Private complaint 2",
            complaints_content="Content 2",
            user=self.patient2
        )

        session = self.client.session
        session['uid'] = self.patient1.id
        session['role'] = 'user'
        session.save()

        response = self.client.get(reverse('User:complaints'))
        self.assertEqual(response.status_code, 200)
        self.assertNotIn(comp2, response.context['complaint'])

    def test_patient_cannot_access_another_patients_order(self):
        """Patient 1 cannot view or pay for Patient 2's booking (IDOR prevention)."""
        booking_patient2 = tbl_booking.objects.create(
            user=self.patient2,
            booking_amount=Decimal("100.00"),
            booking_status=1
        )

        session = self.client.session
        session['uid'] = self.patient1.id
        session['role'] = 'user'
        session.save()

        response = self.client.get(reverse('User:payment', args=[booking_patient2.id]))
        self.assertEqual(response.status_code, 404)

    def test_empty_cart_checkout_does_not_crash(self):
        """Empty cart checkout does not produce UnboundLocalError."""
        session = self.client.session
        session['uid'] = self.patient1.id
        session['role'] = 'user'
        session.save()

        # Submit checkout with no active booking or items
        response = self.client.post(reverse('User:Mycart'))
        self.assertRedirects(response, reverse('User:Mycart'))

    def test_server_calculates_price_ignoring_client_tampering(self):
        """Server-side calculation ignores any manipulated client carttotalamt."""
        session = self.client.session
        session['uid'] = self.patient1.id
        session['role'] = 'user'
        session.save()

        booking = tbl_booking.objects.create(user=self.patient1, booking_status=0)
        # 3 x 20.00 = 60.00
        tbl_cart.objects.create(
            booking=booking,
            medicine=self.otc_med,
            cart_quantity=3,
            cart_status=0
        )

        # Attacker posts 1.00 as carttotalamt
        response = self.client.post(reverse('User:Mycart'), {
            'carttotalamt': '1.00'
        })
        self.assertRedirects(response, reverse('User:payment', args=[booking.id]))

        booking.refresh_from_db()
        # Verify server calculated exactly 60.00, completely ignoring 1.00
        self.assertEqual(booking.booking_amount, Decimal("60.00"))

    def test_insufficient_stock_rejects_checkout(self):
        """Order checkout fails if requested quantity exceeds available stock."""
        session = self.client.session
        session['uid'] = self.patient1.id
        session['role'] = 'user'
        session.save()

        booking = tbl_booking.objects.create(user=self.patient1, booking_status=0)
        # Request 15 units when stock is only 10
        tbl_cart.objects.create(
            booking=booking,
            medicine=self.otc_med,
            cart_quantity=15,
            cart_status=0
        )

        response = self.client.post(reverse('User:Mycart'))
        self.assertRedirects(response, reverse('User:Mycart'))
        booking.refresh_from_db()
        self.assertEqual(booking.booking_status, 0)  # Checkout blocked

    def test_prescription_required_medicine_redirects_to_prescription_upload(self):
        """Cart containing prescription-required medicine directs user to prescription upload."""
        session = self.client.session
        session['uid'] = self.patient1.id
        session['role'] = 'user'
        session.save()

        booking = tbl_booking.objects.create(user=self.patient1, booking_status=0)
        tbl_cart.objects.create(
            booking=booking,
            medicine=self.rx_med,
            cart_quantity=1,
            cart_status=0
        )

        response = self.client.post(reverse('User:Mycart'))
        self.assertRedirects(response, reverse('User:addprescription', args=[booking.id]))

    def test_rating_binds_to_authenticated_user(self):
        """Rating submission uses authenticated user identity, ignoring client spoofing."""
        session = self.client.session
        session['uid'] = self.patient1.id
        session['role'] = 'user'
        session.save()

        # Attacker passes spoofed user_name in POST/GET
        self.client.post(reverse('User:ajaxstar'), {
            'rating_data': '4',
            'user_name': 'SpoofedCelebrity',
            'user_review': 'Great doctor!',
            'pid': self.doctor.id
        })

        rating_obj = tbl_rating.objects.filter(doctor=self.doctor).first()
        self.assertIsNotNone(rating_obj)
        self.assertEqual(rating_obj.user, self.patient1)
        self.assertEqual(rating_obj.user_name, self.patient1.registration_name)
        self.assertEqual(rating_obj.rating_data, 4)

    def test_rating_values_validated(self):
        """Rating values outside 1-5 are clamped or normalized."""
        session = self.client.session
        session['uid'] = self.patient1.id
        session['role'] = 'user'
        session.save()

        # Test value > 5 clamped to 5
        self.client.post(reverse('User:ajaxstar'), {
            'rating_data': '99',
            'user_review': 'Super',
            'pid': self.doctor.id
        })
        rating_obj = tbl_rating.objects.filter(doctor=self.doctor).latest('id')
        self.assertEqual(rating_obj.rating_data, 5)

    def test_viewdoctor_annotated_query(self):
        """viewdoctor correctly annotates average ratings in a single query."""
        tbl_rating.objects.create(
            doctor=self.doctor,
            user=self.patient1,
            user_name="Patient One",
            user_review="Excellent",
            rating_data=5
        )
        tbl_rating.objects.create(
            doctor=self.doctor,
            user=self.patient2,
            user_name="Patient Two",
            user_review="Good",
            rating_data=3
        )

        session = self.client.session
        session['uid'] = self.patient1.id
        session['role'] = 'user'
        session.save()

        response = self.client.get(reverse('User:viewdoctor'))
        self.assertEqual(response.status_code, 200)
        doctor_data = response.context['doctor']
        # Finds self.doctor and verifies average (5 + 3)/2 = 4
        doc_entry = next((item for item in doctor_data if item[0].id == self.doctor.id), None)
        self.assertIsNotNone(doc_entry)
        self.assertEqual(doc_entry[1], 4)

    def test_starrating_aggregation(self):
        """starrating endpoint aggregates counts per rating in SQL."""
        tbl_rating.objects.create(
            doctor=self.doctor,
            user=self.patient1,
            user_name="Patient One",
            user_review="Great",
            rating_data=5
        )
        tbl_rating.objects.create(
            doctor=self.doctor,
            user=self.patient2,
            user_name="Patient Two",
            user_review="Okay",
            rating_data=4
        )

        session = self.client.session
        session['uid'] = self.patient1.id
        session['role'] = 'user'
        session.save()

        response = self.client.get(reverse('User:starrating'), {'pdt': self.doctor.id})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['five'], 1)
        self.assertEqual(data['four'], 1)
        self.assertEqual(data['total_review'], 2)

    def test_cart_unique_constraint(self):
        """Database constraint prevents duplicate medicine in the same booking."""
        from django.db import IntegrityError
        booking = tbl_booking.objects.create(user=self.patient1, booking_status=0)
        tbl_cart.objects.create(
            booking=booking,
            medicine=self.otc_med,
            cart_quantity=1
        )
        with self.assertRaises(IntegrityError):
            tbl_cart.objects.create(
                booking=booking,
                medicine=self.otc_med,
                cart_quantity=2
            )

    def test_rating_check_constraint(self):
        """Database constraint enforces rating_data between 1 and 5."""
        from django.db import IntegrityError
        with self.assertRaises(IntegrityError):
            tbl_rating.objects.create(
                doctor=self.doctor,
                user=self.patient1,
                user_name="Patient",
                user_review="Invalid",
                rating_data=10
            )

    def test_medicine_get_available_stock_method(self):
        """tbl_medicine.get_available_stock accurately reflects stock and deductions."""
        # Initial stock for self.otc_med is 10
        self.assertEqual(self.otc_med.get_available_stock(), 10)

        # Create paid order for 3 items
        paid_booking = tbl_booking.objects.create(user=self.patient1, booking_status=2)
        tbl_cart.objects.create(
            booking=paid_booking,
            medicine=self.otc_med,
            cart_quantity=3,
            cart_status=1
        )
        self.assertEqual(self.otc_med.get_available_stock(), 7)

    def test_duplicate_consultation_request_prevented(self):
        """Prevent patient from submitting duplicate active consultation requests to same doctor."""
        session = self.client.session
        session['uid'] = self.patient1.id
        session['role'] = 'user'
        session.save()

        # First request succeeds
        res1 = self.client.post(reverse('User:request', args=[self.doctor.id]), {
            'details': 'First consultation note'
        })
        self.assertRedirects(res1, reverse('User:viewrequest'))
        self.assertEqual(tbl_request.objects.filter(user=self.patient1, dotor=self.doctor, request_status=0).count(), 1)

        # Second request while first is still pending is rejected
        res2 = self.client.post(reverse('User:request', args=[self.doctor.id]), {
            'details': 'Second duplicate request'
        })
        self.assertRedirects(res2, reverse('User:viewrequest'))
        # Count remains 1
        self.assertEqual(tbl_request.objects.filter(user=self.patient1, dotor=self.doctor, request_status=0).count(), 1)

    def test_patient_cannot_view_another_patients_prescription(self):
        """Patient 2 cannot view Patient 1's consultation prescription (IDOR isolation)."""
        req1 = tbl_request.objects.create(
            request_details="Consultation 1",
            user=self.patient1,
            dotor=self.doctor,
            request_status=1
        )
        tbl_prescription.objects.create(requestpres=req1)

        # Log in as Patient 2
        session = self.client.session
        session['uid'] = self.patient2.id
        session['role'] = 'user'
        session.save()

        response = self.client.get(reverse('User:viewprescription', args=[req1.id]))
        self.assertEqual(response.status_code, 404)

    def test_payment_blocks_if_stock_depleted_before_payment(self):
        """Payment re-verifies stock and blocks payment if stock is depleted between checkout and payment."""
        session = self.client.session
        session['uid'] = self.patient1.id
        session['role'] = 'user'
        session.save()

        # Create checkout-initiated booking for 10 units (all available stock)
        booking = tbl_booking.objects.create(
            user=self.patient1,
            booking_amount=Decimal("200.00"),
            booking_status=1
        )
        tbl_cart.objects.create(
            booking=booking,
            medicine=self.otc_med,
            cart_quantity=10,
            cart_status=1,
            unit_price=Decimal("20.00")
        )

        # Another paid order consumes 5 units before patient completes payment
        paid_booking = tbl_booking.objects.create(user=self.patient2, booking_status=2)
        tbl_cart.objects.create(
            booking=paid_booking,
            medicine=self.otc_med,
            cart_quantity=5,
            cart_status=1,
            unit_price=Decimal("20.00")
        )

        # Patient 1 attempts to pay for 10 units, but only 5 remain
        response = self.client.post(reverse('User:payment', args=[booking.id]))
        self.assertRedirects(response, reverse('User:Mycart'))

        booking.refresh_from_db()
        # Booking must NOT have transitioned to paid (status 2)
        self.assertNotEqual(booking.booking_status, 2)

    def test_ajaxstar_duplicate_updates_existing_review(self):
        """Submitting a second rating updates existing rating instead of duplicating records."""
        session = self.client.session
        session['uid'] = self.patient1.id
        session['role'] = 'user'
        session.save()

        # Initial rating: 3 stars
        self.client.post(reverse('User:ajaxstar'), {
            'rating_data': '3',
            'user_review': 'Average experience',
            'pid': self.doctor.id
        })
        self.assertEqual(tbl_rating.objects.filter(user=self.patient1, doctor=self.doctor).count(), 1)
        r1 = tbl_rating.objects.get(user=self.patient1, doctor=self.doctor)
        self.assertEqual(r1.rating_data, 3)

        # Updated rating: 5 stars
        self.client.post(reverse('User:ajaxstar'), {
            'rating_data': '5',
            'user_review': 'Updated to excellent',
            'pid': self.doctor.id
        })
        self.assertEqual(tbl_rating.objects.filter(user=self.patient1, doctor=self.doctor).count(), 1)
        r1.refresh_from_db()
        self.assertEqual(r1.rating_data, 5)
        self.assertEqual(r1.user_review, 'Updated to excellent')

    def test_invalid_file_upload_rejected_on_prescription(self):
        """Disallowed file extensions (e.g. .exe) are rejected during prescription upload."""
        session = self.client.session
        session['uid'] = self.patient1.id
        session['role'] = 'user'
        session.save()

        booking = tbl_booking.objects.create(
            user=self.patient1,
            booking_amount=Decimal("150.00"),
            booking_status=1
        )

        fake_exe = SimpleUploadedFile("malicious.exe", b"MZexecutabledata", content_type="application/x-msdownload")
        response = self.client.post(reverse('User:addprescription', args=[booking.id]), {
            'prescription': fake_exe
        })

        self.assertEqual(response.status_code, 200)
        booking.refresh_from_db()
        self.assertFalse(bool(booking.prescription))
