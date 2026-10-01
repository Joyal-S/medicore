from django.test import TestCase, Client
from django.urls import reverse
from Admin.models import tbl_district, tbl_place
from Guest.models import tbl_registration, tbl_doctor
from User.models import tbl_rating
from mainproject.security import hash_password


class RatingWorkflowAndSecurityTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.district = tbl_district.objects.create(district_name="Kozhikode")
        self.place = tbl_place.objects.create(place_name="Vadakara", district=self.district)

        self.patient1 = tbl_registration.objects.create(
            registration_name="Reviewer One",
            registration_email="rev1@test.com",
            registration_contact="9876543601",
            registration_address="Vadakara",
            registration_password=hash_password("pw"),
            place=self.place
        )

        self.patient2 = tbl_registration.objects.create(
            registration_name="Reviewer Two",
            registration_email="rev2@test.com",
            registration_contact="9876543602",
            registration_address="Vadakara",
            registration_password=hash_password("pw"),
            place=self.place
        )

        self.doctor = tbl_doctor.objects.create(
            doctor_name="Dr. Nambiar",
            doctor_email="nambiar@test.com",
            doctor_contact="9876543603",
            doctor_password=hash_password("pw"),
            doctor_status=1,
            place=self.place
        )

    def test_submit_valid_rating_bound_to_session_user(self):
        """Rating submission uses session user identity regardless of spoofed form parameters."""
        session = self.client.session
        session['uid'] = self.patient1.id
        session['role'] = 'user'
        session.save()

        response = self.client.post(reverse('User:ajaxstar'), {
            'rating_data': '4',
            'user_review': 'Thorough checkup',
            'user_name': 'HackerName',
            'pid': self.doctor.id
        })
        self.assertEqual(response.status_code, 200)

        rating_entry = tbl_rating.objects.filter(doctor=self.doctor, user=self.patient1).first()
        self.assertIsNotNone(rating_entry)
        self.assertEqual(rating_entry.user, self.patient1)
        self.assertEqual(rating_entry.user_name, self.patient1.registration_name)
        self.assertEqual(rating_entry.rating_data, 4)

    def test_ajaxstar_requires_post_method(self):
        """GET request to ajaxstar is rejected with 405 Method Not Allowed."""
        session = self.client.session
        session['uid'] = self.patient1.id
        session['role'] = 'user'
        session.save()

        res = self.client.get(reverse('User:ajaxstar'))
        self.assertEqual(res.status_code, 405)
        self.assertFalse(tbl_rating.objects.filter(doctor=self.doctor).exists())

    def test_duplicate_review_updates_existing(self):
        """Multiple submissions by the same user update their existing review instead of creating duplicates."""
        session = self.client.session
        session['uid'] = self.patient1.id
        session['role'] = 'user'
        session.save()

        # Review 1
        self.client.post(reverse('User:ajaxstar'), {
            'rating_data': '3',
            'user_review': 'Initial review',
            'pid': self.doctor.id
        })
        self.assertEqual(tbl_rating.objects.filter(doctor=self.doctor, user=self.patient1).count(), 1)

        # Review 2
        self.client.post(reverse('User:ajaxstar'), {
            'rating_data': '5',
            'user_review': 'Follow-up was fantastic',
            'pid': self.doctor.id
        })
        self.assertEqual(tbl_rating.objects.filter(doctor=self.doctor, user=self.patient1).count(), 1)

        r = tbl_rating.objects.get(doctor=self.doctor, user=self.patient1)
        self.assertEqual(r.rating_data, 5)
        self.assertEqual(r.user_review, 'Follow-up was fantastic')

    def test_rating_breakdown_json_endpoint(self):
        """starrating endpoint aggregates counts per rating bracket."""
        session = self.client.session
        session['uid'] = self.patient1.id
        session['role'] = 'user'
        session.save()

        tbl_rating.objects.create(doctor=self.doctor, user=self.patient1, user_name="P1", rating_data=5)
        tbl_rating.objects.create(doctor=self.doctor, user=self.patient2, user_name="P2", rating_data=4)

        res = self.client.get(reverse('User:starrating'), {'pdt': self.doctor.id})
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data['five'], 1)
        self.assertEqual(data['four'], 1)
        self.assertEqual(data['three'], 0)
        self.assertEqual(data['total_review'], 2)
