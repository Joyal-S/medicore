from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.hashers import check_password
from Admin.models import tbl_district, tbl_place, tbl_adminregistration
from Guest.models import tbl_registration, tbl_doctor, tbl_shop
from mainproject.security import hash_password


class AuthenticationTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.district = tbl_district.objects.create(district_name="Idukki")
        self.place = tbl_place.objects.create(place_name="Thodupuzha", district=self.district)

        # Create Patient
        self.user_password = "userSecret123"
        self.user = tbl_registration.objects.create(
            registration_name="John Doe",
            registration_email="john@example.com",
            registration_contact="9876543210",
            registration_address="Main Street",
            registration_password=hash_password(self.user_password),
            place=self.place
        )

        # Create Pending & Approved Doctors
        self.doc_password = "docSecret123"
        self.pending_doc = tbl_doctor.objects.create(
            doctor_name="Pending Doc",
            doctor_email="pending_doc@example.com",
            doctor_contact="1234567890",
            doctor_password=hash_password(self.doc_password),
            doctor_status=0,
            place=self.place
        )
        self.approved_doc = tbl_doctor.objects.create(
            doctor_name="Approved Doc",
            doctor_email="approved_doc@example.com",
            doctor_contact="1234567891",
            doctor_password=hash_password(self.doc_password),
            doctor_status=1,
            place=self.place
        )

        # Create Pending & Approved Shops
        self.shop_password = "shopSecret123"
        self.pending_shop = tbl_shop.objects.create(
            shop_name="Pending Pharmacy",
            shop_email="pending_shop@example.com",
            shop_contact="1234567892",
            shop_password=hash_password(self.shop_password),
            shop_status=0,
            place=self.place
        )
        self.approved_shop = tbl_shop.objects.create(
            shop_name="Approved Pharmacy",
            shop_email="approved_shop@example.com",
            shop_contact="1234567893",
            shop_password=hash_password(self.shop_password),
            shop_status=1,
            place=self.place
        )

        # Create Admin
        self.admin_password = "adminSecret123"
        self.admin = tbl_adminregistration.objects.create(
            registration_name="Admin Master",
            registration_email="admin@example.com",
            registration_password=hash_password(self.admin_password)
        )

    def test_registration_hashes_password(self):
        """User registration stores hashed password, never plaintext."""
        response = self.client.post(reverse('Guest:registration'), {
            'name': 'New Patient',
            'email': 'newpatient@example.com',
            'contact': '9876543210',
            'address': 'Test Address',
            'place': self.place.id,
            'password': 'myPlaintextPassword123'
        })
        self.assertEqual(response.status_code, 302)
        created_user = tbl_registration.objects.get(registration_email='newpatient@example.com')
        self.assertNotEqual(created_user.registration_password, 'myPlaintextPassword123')
        self.assertTrue(check_password('myPlaintextPassword123', created_user.registration_password))

    def test_valid_user_login(self):
        """Valid credentials correctly log the user in and set session."""
        response = self.client.post(reverse('Guest:login'), {
            'email': 'john@example.com',
            'password': self.user_password
        })
        self.assertRedirects(response, reverse('User:home'))
        self.assertEqual(self.client.session.get('uid'), self.user.id)
        self.assertEqual(self.client.session.get('role'), 'user')

    def test_invalid_password_login(self):
        """Invalid password fails login."""
        response = self.client.post(reverse('Guest:login'), {
            'email': 'john@example.com',
            'password': 'wrongPassword'
        })
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(self.client.session.get('uid'))
        self.assertIn('msg', response.context)

    def test_unapproved_doctor_cannot_login(self):
        """Doctor with status=0 cannot login."""
        response = self.client.post(reverse('Guest:login'), {
            'email': 'pending_doc@example.com',
            'password': self.doc_password
        })
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(self.client.session.get('did'))
        self.assertIn('pending', response.context['msg'].lower())

    def test_approved_doctor_can_login(self):
        """Approved doctor with status=1 logs in successfully."""
        response = self.client.post(reverse('Guest:login'), {
            'email': 'approved_doc@example.com',
            'password': self.doc_password
        })
        self.assertRedirects(response, reverse('Doctor:home'))
        self.assertEqual(self.client.session.get('did'), self.approved_doc.id)

    def test_unapproved_shop_cannot_login(self):
        """Shop with status=0 cannot login."""
        response = self.client.post(reverse('Guest:login'), {
            'email': 'pending_shop@example.com',
            'password': self.shop_password
        })
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(self.client.session.get('sid'))
        self.assertIn('pending', response.context['msg'].lower())

    def test_approved_shop_can_login(self):
        """Approved shop logs in successfully."""
        response = self.client.post(reverse('Guest:login'), {
            'email': 'approved_shop@example.com',
            'password': self.shop_password
        })
        self.assertRedirects(response, reverse('Shop:home'))
        self.assertEqual(self.client.session.get('sid'), self.approved_shop.id)

    def test_admin_login(self):
        """Admin logs in successfully."""
        response = self.client.post(reverse('Guest:login'), {
            'email': 'admin@example.com',
            'password': self.admin_password
        })
        self.assertRedirects(response, reverse('Admin:home'))
        self.assertEqual(self.client.session.get('aid'), self.admin.id)

    def test_user_logout(self):
        """Logout clears the session."""
        self.client.post(reverse('Guest:login'), {
            'email': 'john@example.com',
            'password': self.user_password
        })
        self.assertEqual(self.client.session.get('uid'), self.user.id)
        logout_response = self.client.get(reverse('User:ulogout'))
        self.assertRedirects(logout_response, reverse('Guest:login'))
        self.assertIsNone(self.client.session.get('uid'))
