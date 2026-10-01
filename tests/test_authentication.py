from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.hashers import check_password
from Admin.models import tbl_district, tbl_place, tbl_adminregistration
from Guest.models import tbl_registration, tbl_doctor, tbl_shop
from mainproject.security import hash_password, verify_and_upgrade_password


class AuthenticationAndSessionTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.district = tbl_district.objects.create(district_name="Kollam")
        self.place = tbl_place.objects.create(place_name="Chavara", district=self.district)

        self.patient_pass = "patientSecret123"
        self.patient = tbl_registration.objects.create(
            registration_name="Kollam Patient",
            registration_email="patient_auth@test.com",
            registration_contact="9876543201",
            registration_address="Chavara",
            registration_password=hash_password(self.patient_pass),
            place=self.place
        )

        self.doctor_pass = "doctorSecret123"
        self.approved_doctor = tbl_doctor.objects.create(
            doctor_name="Dr. Approved",
            doctor_email="doc_auth@test.com",
            doctor_contact="9876543202",
            doctor_password=hash_password(self.doctor_pass),
            doctor_status=1,
            place=self.place
        )

        self.pending_doctor = tbl_doctor.objects.create(
            doctor_name="Dr. Pending",
            doctor_email="doc_pending@test.com",
            doctor_contact="9876543203",
            doctor_password=hash_password(self.doctor_pass),
            doctor_status=0,
            place=self.place
        )

        self.rejected_doctor = tbl_doctor.objects.create(
            doctor_name="Dr. Rejected",
            doctor_email="doc_rejected@test.com",
            doctor_contact="9876543204",
            doctor_password=hash_password(self.doctor_pass),
            doctor_status=2,
            place=self.place
        )

        self.shop_pass = "shopSecret123"
        self.approved_shop = tbl_shop.objects.create(
            shop_name="Approved Meds",
            shop_email="shop_auth@test.com",
            shop_contact="9876543205",
            shop_password=hash_password(self.shop_pass),
            shop_status=1,
            place=self.place
        )

        self.pending_shop = tbl_shop.objects.create(
            shop_name="Pending Meds",
            shop_email="shop_pending@test.com",
            shop_contact="9876543206",
            shop_password=hash_password(self.shop_pass),
            shop_status=0,
            place=self.place
        )

        self.rejected_shop = tbl_shop.objects.create(
            shop_name="Rejected Meds",
            shop_email="shop_rejected@test.com",
            shop_contact="9876543207",
            shop_password=hash_password(self.shop_pass),
            shop_status=2,
            place=self.place
        )

        self.admin_pass = "adminSecret123"
        self.admin = tbl_adminregistration.objects.create(
            registration_name="Main Admin",
            registration_email="admin_auth@test.com",
            registration_password=hash_password(self.admin_pass)
        )

    def test_duplicate_registration_rejected(self):
        """User registration with existing email is rejected."""
        response = self.client.post(reverse('Guest:registration'), {
            'name': 'Duplicate User',
            'email': 'patient_auth@test.com',
            'contact': '9876543210',
            'address': 'Test Address',
            'place': self.place.id,
            'password': 'ValidPassword123'
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(tbl_registration.objects.filter(registration_email='patient_auth@test.com').count(), 1)

    def test_duplicate_doctor_registration_rejected(self):
        """Doctor registration with existing email is rejected."""
        response = self.client.post(reverse('Guest:doctor'), {
            'name': 'Duplicate Doctor',
            'email': 'doc_auth@test.com',
            'contact': '9876543210',
            'place': self.place.id,
            'password': 'ValidPassword123'
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(tbl_doctor.objects.filter(doctor_email='doc_auth@test.com').count(), 1)

    def test_duplicate_shop_registration_rejected(self):
        """Shop registration with existing email is rejected."""
        response = self.client.post(reverse('Guest:shop'), {
            'shop_name': 'Duplicate Shop',
            'email': 'shop_auth@test.com',
            'contact': '9876543210',
            'address': 'Test',
            'place': self.place.id,
            'password': 'ValidPassword123'
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(tbl_shop.objects.filter(shop_email='shop_auth@test.com').count(), 1)

    def test_rejected_doctor_and_shop_cannot_login(self):
        """Rejected accounts (status=2) cannot log into the system."""
        # Rejected doctor
        res_doc = self.client.post(reverse('Guest:login'), {
            'email': 'doc_rejected@test.com',
            'password': self.doctor_pass
        })
        self.assertEqual(res_doc.status_code, 200)
        self.assertIsNone(self.client.session.get('did'))
        self.assertIn('rejected', res_doc.context['msg'].lower())

        # Rejected shop
        res_shop = self.client.post(reverse('Guest:login'), {
            'email': 'shop_rejected@test.com',
            'password': self.shop_pass
        })
        self.assertEqual(res_shop.status_code, 200)
        self.assertIsNone(self.client.session.get('sid'))
        self.assertIn('rejected', res_shop.context['msg'].lower())

    def test_legacy_plaintext_password_auto_upgrade(self):
        """Legacy plaintext passwords verify successfully and are upgraded to hashes on login."""
        legacy_patient = tbl_registration.objects.create(
            registration_name="Legacy User",
            registration_email="legacy@test.com",
            registration_contact="9876543299",
            registration_address="Town",
            registration_password="plaintextLegacyPassword123",
            place=self.place
        )

        res = self.client.post(reverse('Guest:login'), {
            'email': 'legacy@test.com',
            'password': 'plaintextLegacyPassword123'
        })
        self.assertRedirects(res, reverse('User:home'))

        legacy_patient.refresh_from_db()
        self.assertNotEqual(legacy_patient.registration_password, "plaintextLegacyPassword123")
        self.assertTrue(check_password("plaintextLegacyPassword123", legacy_patient.registration_password))

    def test_unauthenticated_cannot_access_user_endpoints(self):
        """Direct access to protected patient pages without session redirects to login."""
        endpoints = [
            reverse('User:home'),
            reverse('User:Mycart'),
            reverse('User:myorder'),
            reverse('User:viewrequest'),
            reverse('User:notifications'),
            reverse('User:search'),
        ]
        for ep in endpoints:
            response = self.client.get(ep)
            self.assertRedirects(response, reverse('Guest:login'))

    def test_tampered_session_flushed_and_redirected(self):
        """If session has an ID for a nonexistent record, session is flushed and user redirected."""
        session = self.client.session
        session['uid'] = 999999  # nonexistent
        session['role'] = 'user'
        session.save()

        response = self.client.get(reverse('User:home'))
        self.assertRedirects(response, reverse('Guest:login'))
        self.assertNotIn('uid', self.client.session)
