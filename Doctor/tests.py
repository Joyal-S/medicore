from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, Client
from django.urls import reverse
from Admin.models import tbl_district, tbl_place
from Guest.models import tbl_registration, tbl_doctor
from User.models import tbl_request, tbl_prescription
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

    def test_doctor_prescription_creation_atomic(self):
        """Doctor uploads valid prescription: request_status transitions to 1 and tbl_prescription is created."""
        session = self.client.session
        session['did'] = self.doctor1.id
        session['role'] = 'doctor'
        session.save()

        pdf_file = SimpleUploadedFile("prescription.pdf", b"%PDF-1.4...", content_type="application/pdf")
        response = self.client.post(reverse('Doctor:prescription', args=[self.req1.id]), {
            'file': pdf_file
        })
        self.assertRedirects(response, reverse('Doctor:viewrequest'))

        self.req1.refresh_from_db()
        self.assertEqual(self.req1.request_status, 1)
        self.assertTrue(tbl_prescription.objects.filter(requestpres=self.req1).exists())

    def test_doctor_prescription_rejects_disallowed_file(self):
        """Disallowed file upload (e.g. .exe) is rejected and does not update request status."""
        session = self.client.session
        session['did'] = self.doctor1.id
        session['role'] = 'doctor'
        session.save()

        fake_exe = SimpleUploadedFile("malware.exe", b"MZmaliciouspayload", content_type="application/x-msdownload")
        response = self.client.post(reverse('Doctor:prescription', args=[self.req1.id]), {
            'file': fake_exe
        })
        self.assertEqual(response.status_code, 200)

        self.req1.refresh_from_db()
        self.assertEqual(self.req1.request_status, 0)
        self.assertFalse(tbl_prescription.objects.filter(requestpres=self.req1).exists())

    def test_ml_differential_diagnosis_generation(self):
        """ML service produces top differential diagnosis possibilities with probabilities."""
        symptoms = ['chills', 'vomiting', 'high_fever', 'sweating', 'headache']
        result = predict_from_symptoms(symptoms, top_k=3)
        self.assertTrue(result['success'])
        self.assertIn('differential_diagnosis', result)
        self.assertGreaterEqual(len(result['differential_diagnosis']), 1)
        for diff in result['differential_diagnosis']:
            self.assertIn('condition', diff)
            self.assertIn('probability', diff)
            self.assertGreaterEqual(diff['probability'], 0.0)
            self.assertLessEqual(diff['probability'], 100.0)

    def test_ml_maximum_symptoms_bound(self):
        """Excessive symptoms exceeding MAX_SYMPTOM_SELECTION_LIMIT are rejected with validation error."""
        too_many = RAW_SYMPTOMS[:28]  # 28 symptoms exceeds limit of 25
        result = predict_from_symptoms(too_many)
        self.assertFalse(result['success'])
        self.assertIsNone(result['predicted_disease'])
        self.assertIn("Maximum allowed is 25", result['error'])

    def test_ml_duplicate_symptoms_handling(self):
        """Duplicate symptom entries in user input are deduplicated seamlessly."""
        symptoms = ['itching', 'itching', 'skin_rash', 'skin_rash']
        result = predict_from_symptoms(symptoms)
        self.assertTrue(result['success'])
        self.assertEqual(len(result['symptoms_selected']), 2)

    def test_doctor_checkdisease_ajax_endpoint(self):
        """Doctor checkdisease AJAX submission returns structured JSON and persists confidence."""
        session = self.client.session
        session['did'] = self.doctor1.id
        session['role'] = 'doctor'
        session.save()

        response = self.client.post(
            reverse('Doctor:checkdisease', args=[self.req1.id]),
            data={'symptoms[]': ['itching', 'skin_rash', 'nodal_skin_eruptions']},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertIn('predicted_disease', data['data'])
        self.assertIn('Fungal infection', data['data']['predicted_disease'])

        # Verify record was stored with confidence score
        prediction_record = tbl_disease.objects.filter(reqpre=self.req1).first()
        self.assertIsNotNone(prediction_record)
        self.assertEqual(prediction_record.disease_name, 'Fungal infection')
        self.assertIsNotNone(prediction_record.confidence_score)
        self.assertGreater(prediction_record.confidence_score, 50.0)

    def test_doctor_checkdisease_ajax_validation_error(self):
        """AJAX submission with empty symptoms returns 400 error and does not create database record."""
        session = self.client.session
        session['did'] = self.doctor1.id
        session['role'] = 'doctor'
        session.save()

        initial_count = tbl_disease.objects.count()
        response = self.client.post(
            reverse('Doctor:checkdisease', args=[self.req1.id]),
            data={'symptoms[]': []},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertFalse(data['success'])
        self.assertEqual(tbl_disease.objects.count(), initial_count)

    def test_doctor_prescription_sends_notification_to_patient(self):
        """When doctor issues prescription, a notification is generated for the patient."""
        from User.models import tbl_notification
        session = self.client.session
        session['did'] = self.doctor1.id
        session['role'] = 'doctor'
        session.save()

        pdf_file = SimpleUploadedFile("rx.pdf", b"%PDF-1.4 sample content", content_type="application/pdf")
        self.client.post(reverse('Doctor:prescription', args=[self.req1.id]), {
            'file': pdf_file
        })

        patient_notif = tbl_notification.objects.filter(user=self.user).first()
        self.assertIsNotNone(patient_notif)
        self.assertIn("Prescription", patient_notif.title)
        self.assertEqual(patient_notif.notification_type, "prescription")

    def test_doctor_viewrequest_pagination(self):
        """Consultation requests list paginates cleanly across page boundaries."""
        session = self.client.session
        session['did'] = self.doctor1.id
        session['role'] = 'doctor'
        session.save()

        # Create 12 additional consultation requests for doctor 1 (total 13 requests)
        for i in range(12):
            tbl_request.objects.create(
                request_details=f"Patient consultation request #{i+2}",
                user=self.user,
                dotor=self.doctor1,
                request_status=0
            )

        # Page 1 (10 per page)
        res_p1 = self.client.get(reverse('Doctor:viewrequest') + '?page=1')
        self.assertEqual(res_p1.status_code, 200)
        self.assertEqual(len(res_p1.context['page_obj']), 10)
        self.assertTrue(res_p1.context['page_obj'].has_next())

        # Page 2 (3 items remaining)
        res_p2 = self.client.get(reverse('Doctor:viewrequest') + '?page=2')
        self.assertEqual(res_p2.status_code, 200)
        self.assertEqual(len(res_p2.context['page_obj']), 3)
        self.assertFalse(res_p2.context['page_obj'].has_next())

