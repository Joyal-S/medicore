from django.test import TestCase, Client
from django.urls import reverse
from Admin.models import tbl_district, tbl_place
from Guest.models import tbl_registration, tbl_doctor
from User.models import tbl_request
from Doctor.models import tbl_disease
from Doctor.ml_service import predict_from_symptoms, RAW_SYMPTOMS
from mainproject.security import hash_password


class DoctorAndMLTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.district = tbl_district.objects.create(district_name="Kottayam")
        self.place = tbl_place.objects.create(place_name="Pala", district=self.district)

        self.user = tbl_registration.objects.create(
            registration_name="Alice",
            registration_email="alice@test.com",
            registration_contact="1234567890",
            registration_address="Pala town",
            registration_password=hash_password("userpass"),
            place=self.place
        )

        self.doctor1 = tbl_doctor.objects.create(
            doctor_name="Doctor One",
            doctor_email="doc1@test.com",
            doctor_contact="1111111111",
            doctor_password=hash_password("docpass"),
            doctor_status=1,
            place=self.place
        )

        self.doctor2 = tbl_doctor.objects.create(
            doctor_name="Doctor Two",
            doctor_email="doc2@test.com",
            doctor_contact="2222222222",
            doctor_password=hash_password("docpass"),
            doctor_status=1,
            place=self.place
        )

        # Request assigned to Doctor 1
        self.req1 = tbl_request.objects.create(
            request_details="Severe headache and fever",
            user=self.user,
            dotor=self.doctor1,
            request_status=0
        )

    def test_doctor_cannot_access_another_doctors_request(self):
        """Doctor 2 cannot access checkdisease for Doctor 1's request (IDOR prevention)."""
        session = self.client.session
        session['did'] = self.doctor2.id
        session['role'] = 'doctor'
        session.save()

        # Doctor 2 tries to access Doctor 1's consultation request
        response = self.client.get(reverse('Doctor:checkdisease', args=[self.req1.id]))
        self.assertEqual(response.status_code, 404)

    def test_doctor_cannot_prescribe_for_another_doctors_request(self):
        """Doctor 2 cannot upload prescription for Doctor 1's request."""
        session = self.client.session
        session['did'] = self.doctor2.id
        session['role'] = 'doctor'
        session.save()

        response = self.client.get(reverse('Doctor:prescription', args=[self.req1.id]))
        self.assertEqual(response.status_code, 404)

    def test_ml_prediction_with_valid_symptoms(self):
        """ML service successfully generates prediction for valid symptoms."""
        symptoms = ['itching', 'skin_rash', 'nodal_skin_eruptions']
        result = predict_from_symptoms(symptoms)

        self.assertIsNotNone(result['predicted_disease'])
        self.assertGreater(result['confidence_score'], 0)
        self.assertIn('Fungal infection', result['predicted_disease'])
        self.assertIn('Itching', result['symptoms_selected'])
        self.assertIn('clinical', result['disclaimer'].lower())

    def test_ml_prediction_with_cleaned_symptom_names(self):
        """ML service handles cleaned/special-case symptom strings without error."""
        symptoms = ['spotting_ urination', 'foul_smell_of urine', 'dischromic _patches']
        result = predict_from_symptoms(symptoms)

        self.assertIsNotNone(result['predicted_disease'])
        self.assertIn('Spotting Urination', result['symptoms_selected'])
        self.assertIn('Foul Smell Of Urine', result['symptoms_selected'])
        self.assertIn('Dischromic Patches', result['symptoms_selected'])

    def test_ml_prediction_with_empty_or_unknown_symptoms(self):
        """Empty symptom list returns None without crashing."""
        result = predict_from_symptoms([])
        self.assertIsNone(result['predicted_disease'])
        self.assertEqual(result['confidence_score'], 0)

        # Unknown symptom name
        unknown_result = predict_from_symptoms(['completely_unknown_symptom_xyz'])
        self.assertIsNotNone(unknown_result['disclaimer'])

    def test_ml_feature_vector_length(self):
        """Feature vector matches exact 132 symptoms required by the model."""
        self.assertEqual(len(RAW_SYMPTOMS), 132)
