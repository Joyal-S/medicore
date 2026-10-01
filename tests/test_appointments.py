from django.test import TestCase, Client
from django.urls import reverse
from Admin.models import tbl_district, tbl_place
from Guest.models import tbl_registration, tbl_doctor
from User.models import tbl_request, tbl_notification
from mainproject.security import hash_password


class ConsultationRequestAndAppointmentTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.district = tbl_district.objects.create(district_name="Kottayam")
        self.place = tbl_place.objects.create(place_name="Changanassery", district=self.district)

        self.patient = tbl_registration.objects.create(
            registration_name="Appointment User",
            registration_email="appt_user@test.com",
            registration_contact="9876543401",
            registration_address="Changanassery",
            registration_password=hash_password("pw"),
            place=self.place
        )

        self.doctor1 = tbl_doctor.objects.create(
            doctor_name="Dr. Mathews",
            doctor_email="mathews@test.com",
            doctor_contact="9876543402",
            doctor_password=hash_password("pw"),
            doctor_status=1,
            place=self.place
        )

        self.doctor2 = tbl_doctor.objects.create(
            doctor_name="Dr. Varma",
            doctor_email="varma@test.com",
            doctor_contact="9876543403",
            doctor_password=hash_password("pw"),
            doctor_status=1,
            place=self.place
        )

    def test_create_valid_consultation_request_and_notify_doctor(self):
        """Patient submits consultation request; record is created and doctor receives notification."""
        session = self.client.session
        session['uid'] = self.patient.id
        session['role'] = 'user'
        session.save()

        response = self.client.post(reverse('User:request', args=[self.doctor1.id]), {
            'details': 'Persistent fever and cough for three days.'
        })
        self.assertRedirects(response, reverse('User:viewrequest'))

        req = tbl_request.objects.filter(user=self.patient, dotor=self.doctor1).first()
        self.assertIsNotNone(req)
        self.assertEqual(req.request_status, 0)

        # Check doctor received notification
        notif = tbl_notification.objects.filter(doctor=self.doctor1).first()
        self.assertIsNotNone(notif)
        self.assertIn("Consultation Request", notif.title)

    def test_duplicate_pending_consultation_request_prevented(self):
        """Patient cannot spam multiple pending consultation requests to the same doctor."""
        session = self.client.session
        session['uid'] = self.patient.id
        session['role'] = 'user'
        session.save()

        # First request
        self.client.post(reverse('User:request', args=[self.doctor1.id]), {'details': 'First note'})
        self.assertEqual(tbl_request.objects.filter(user=self.patient, dotor=self.doctor1).count(), 1)

        # Second request
        self.client.post(reverse('User:request', args=[self.doctor1.id]), {'details': 'Second note'})
        # Still 1
        self.assertEqual(tbl_request.objects.filter(user=self.patient, dotor=self.doctor1).count(), 1)

    def test_empty_details_rejected(self):
        """Consultation request with blank details is rejected."""
        session = self.client.session
        session['uid'] = self.patient.id
        session['role'] = 'user'
        session.save()

        res = self.client.post(reverse('User:request', args=[self.doctor1.id]), {'details': '   '})
        self.assertEqual(res.status_code, 200)
        self.assertFalse(tbl_request.objects.filter(user=self.patient, dotor=self.doctor1).exists())
