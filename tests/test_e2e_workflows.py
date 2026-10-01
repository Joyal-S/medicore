from decimal import Decimal
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, Client
from django.urls import reverse
from Admin.models import tbl_district, tbl_place
from Guest.models import tbl_registration, tbl_doctor, tbl_shop
from Shop.models import tbl_category, tbl_medicine, tbl_stock
from User.models import tbl_booking, tbl_cart, tbl_request, tbl_prescription, tbl_rating
from Doctor.models import tbl_disease
from Doctor.ml_service import predict_from_symptoms
from mainproject.security import hash_password


class EndToEndSystemWorkflowsTest(TestCase):
    """
    Executes the 5 realistic End-to-End Workflows requested in Phase 7 Section 26.
    """
    def setUp(self):
        self.client = Client()
        self.district = tbl_district.objects.create(district_name="Ernakulam")
        self.place = tbl_place.objects.create(place_name="Edappally", district=self.district)
        self.category = tbl_category.objects.create(category_name="Respiratory")

    def test_e2e_workflow_1_patient_registration_to_order(self):
        """TEST 1: Patient -> Register -> Login -> Search medicine -> Add to cart -> Checkout -> Order -> View order."""
        client = Client()
        raw_password = "SecurePassword123"

        # 1. Register Patient
        reg_response = client.post(reverse('Guest:registration'), {
            'name': 'E2E Patient',
            'email': 'e2e_patient@example.com',
            'contact': '9876543210',
            'address': 'Edappally North',
            'place': self.place.id,
            'password': raw_password
        })
        self.assertEqual(reg_response.status_code, 302)
        patient = tbl_registration.objects.get(registration_email='e2e_patient@example.com')

        # 2. Login
        login_res = client.post(reverse('Guest:login'), {
            'email': 'e2e_patient@example.com',
            'password': raw_password
        })
        self.assertRedirects(login_res, reverse('User:home'))
        self.assertEqual(client.session.get('uid'), patient.id)

        # Create active approved pharmacy with stock
        shop = tbl_shop.objects.create(
            shop_name="E2E MedStore",
            shop_email="e2e_shop@example.com",
            shop_contact="9876543211",
            shop_password=hash_password("pw"),
            shop_status=1,
            place=self.place
        )
        med = tbl_medicine.objects.create(
            medicine_name="Inhaler 100mcg",
            medicine_details="Respiratory asthma inhaler",
            medicine_price=Decimal("180.00"),
            shop=shop,
            category=self.category,
            medicine_status=0  # OTC
        )
        tbl_stock.objects.create(medicine=med, stock_qty=20)

        # 3. Search Medicine
        search_res = client.get(reverse('User:search') + '?q=Inhaler')
        self.assertEqual(search_res.status_code, 200)
        self.assertIn(med, search_res.context['med'])

        # 4. Add to Cart
        add_res = client.get(reverse('User:Addcart', args=[med.id]))
        self.assertRedirects(add_res, reverse('User:Mycart'))

        booking = tbl_booking.objects.get(user=patient, booking_status=0)
        cart_item = tbl_cart.objects.get(booking=booking, medicine=med)
        self.assertEqual(cart_item.cart_quantity, 1)

        # 5. Checkout
        checkout_res = client.post(reverse('User:Mycart'))
        self.assertRedirects(checkout_res, reverse('User:payment', args=[booking.id]))
        booking.refresh_from_db()
        self.assertEqual(booking.booking_status, 1)  # Checkout completed

        # 6. Complete Payment
        pay_res = client.post(reverse('User:payment', args=[booking.id]))
        self.assertRedirects(pay_res, reverse('User:payment_suc'))
        booking.refresh_from_db()
        self.assertEqual(booking.booking_status, 2)  # Placed/Paid
        self.assertEqual(med.get_available_stock(), 19)

        # 7. View Orders
        orders_res = client.get(reverse('User:myorder'))
        self.assertEqual(orders_res.status_code, 200)
        self.assertIn(booking, orders_res.context['orders'])

    def test_e2e_workflow_2_doctor_appointment_and_prescription(self):
        """TEST 2: Doctor -> Login -> Appointment -> Create prescription -> Patient receives."""
        client_doc = Client()
        client_pat = Client()
        doc_pass = "DoctorPassword123"

        # Create approved doctor
        doctor = tbl_doctor.objects.create(
            doctor_name="Dr. E2E Pulmonologist",
            doctor_email="e2e_doc@example.com",
            doctor_contact="9876543212",
            doctor_password=hash_password(doc_pass),
            doctor_status=1,
            place=self.place
        )

        patient = tbl_registration.objects.create(
            registration_name="Consulting Patient",
            registration_email="consult_pat@example.com",
            registration_contact="9876543213",
            registration_address="Edappally",
            registration_password=hash_password("pw"),
            place=self.place
        )

        # Patient books consultation
        session_p = client_pat.session
        session_p['uid'] = patient.id
        session_p['role'] = 'user'
        session_p.save()

        client_pat.post(reverse('User:request', args=[doctor.id]), {'details': 'Wheezing and shortness of breath'})
        req = tbl_request.objects.get(user=patient, dotor=doctor)
        self.assertEqual(req.request_status, 0)

        # Doctor logs in
        login_res = client_doc.post(reverse('Guest:login'), {
            'email': 'e2e_doc@example.com',
            'password': doc_pass
        })
        self.assertRedirects(login_res, reverse('Doctor:home'))

        # Doctor views requests
        view_res = client_doc.get(reverse('Doctor:viewrequest'))
        self.assertEqual(view_res.status_code, 200)
        self.assertIn(req, view_res.context['requestview'])

        # Doctor uploads prescription
        pdf_file = SimpleUploadedFile("rx_inhaler.pdf", b"%PDF-1.4 prescription", content_type="application/pdf")
        rx_res = client_doc.post(reverse('Doctor:prescription', args=[req.id]), {'file': pdf_file})
        self.assertRedirects(rx_res, reverse('Doctor:viewrequest'))

        req.refresh_from_db()
        self.assertEqual(req.request_status, 1)  # Prescribed
        self.assertTrue(tbl_prescription.objects.filter(requestpres=req).exists())

        # Patient views their prescription
        pat_rx_res = client_pat.get(reverse('User:viewprescription', args=[req.id]))
        self.assertEqual(pat_rx_res.status_code, 200)

    def test_e2e_workflow_3_pharmacy_inventory_and_order_fulfillment(self):
        """TEST 3: Pharmacy -> Login -> Add medicine -> Receive order -> Update order status."""
        client_shop = Client()
        shop_pass = "PharmacyPass123"

        shop = tbl_shop.objects.create(
            shop_name="Fulfillment Pharmacy",
            shop_email="fulfill_shop@example.com",
            shop_contact="9876543214",
            shop_password=hash_password(shop_pass),
            shop_status=1,
            place=self.place
        )

        patient = tbl_registration.objects.create(
            registration_name="Orderer",
            registration_email="orderer@example.com",
            registration_contact="9876543215",
            registration_address="Road",
            registration_password=hash_password("pw"),
            place=self.place
        )

        # Pharmacy Login
        login_res = client_shop.post(reverse('Guest:login'), {
            'email': 'fulfill_shop@example.com',
            'password': shop_pass
        })
        self.assertRedirects(login_res, reverse('Shop:home'))

        # Add Medicine
        add_med_res = client_shop.post(reverse('Shop:medicine'), {
            'medicine_name': 'Cough Syrup 100ml',
            'medicine_details': 'Soothes throat irritation',
            'medicine_price': '65.00',
            'sel_category': self.category.id,
            'in_stock': 'no'
        })
        self.assertRedirects(add_med_res, reverse('Shop:medicine'))
        med = tbl_medicine.objects.get(medicine_name='Cough Syrup 100ml')

        # Add Stock
        client_shop.post(reverse('Shop:addstock', args=[med.id]), {'stock_qty': '30'})
        self.assertEqual(med.get_available_stock(), 30)

        # Patient buys medicine
        booking = tbl_booking.objects.create(user=patient, booking_amount=Decimal("65.00"), booking_status=2)
        tbl_cart.objects.create(booking=booking, medicine=med, cart_quantity=1, cart_status=1, unit_price=Decimal("65.00"))

        # Pharmacy receives and views order
        view_booking_res = client_shop.get(reverse('Shop:booking'))
        self.assertEqual(view_booking_res.status_code, 200)
        self.assertIn(booking, view_booking_res.context['booking'])

        # Update order status to Packing (2 -> 3)
        pack_res = client_shop.post(reverse('Shop:packing', args=[booking.id]))
        self.assertRedirects(pack_res, reverse('Shop:booking'))
        booking.refresh_from_db()
        self.assertEqual(booking.booking_status, 3)

        # Update order status to Delivered (3 -> 4)
        del_res = client_shop.post(reverse('Shop:delivery', args=[booking.id]))
        self.assertRedirects(del_res, reverse('Shop:booking'))
        booking.refresh_from_db()
        self.assertEqual(booking.booking_status, 4)

    def test_e2e_workflow_4_patient_ml_prediction_and_consultation(self):
        """TEST 4: Patient/Doctor -> Select symptoms -> ML prediction -> View result."""
        symptoms = ['continuous_sneezing', 'chills', 'cough', 'high_fever', 'breathlessness']
        result = predict_from_symptoms(symptoms, top_k=3)

        self.assertTrue(result['success'])
        self.assertIsNotNone(result['predicted_disease'])
        self.assertGreater(result['confidence_score'], 0.0)
        self.assertIn('decision-support', result['disclaimer'].lower())
        self.assertGreaterEqual(len(result['differential_diagnosis']), 1)

    def test_e2e_workflow_5_unauthorized_user_idor_blocked(self):
        """TEST 5: Unauthorized user -> Attempt to access another user's data -> Verify access denied."""
        client = Client()
        victim = tbl_registration.objects.create(
            registration_name="Victim User",
            registration_email="victim@example.com",
            registration_contact="9876543216",
            registration_address="Victim St",
            registration_password=hash_password("pw"),
            place=self.place
        )
        attacker = tbl_registration.objects.create(
            registration_name="Attacker User",
            registration_email="attacker@example.com",
            registration_contact="9876543217",
            registration_address="Attacker St",
            registration_password=hash_password("pw"),
            place=self.place
        )

        victim_booking = tbl_booking.objects.create(user=victim, booking_amount=Decimal("200.00"), booking_status=1)

        # Attacker logs in
        session = client.session
        session['uid'] = attacker.id
        session['role'] = 'user'
        session.save()

        # Attacker tries to access victim's payment page
        res = client.get(reverse('User:payment', args=[victim_booking.id]))
        self.assertEqual(res.status_code, 404)
