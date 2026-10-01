from django.test import TestCase, Client
from django.urls import reverse
from Admin.models import tbl_district, tbl_place, tbl_adminregistration, tbl_audit_log
from Guest.models import tbl_registration, tbl_doctor, tbl_shop
from User.models import tbl_complaints, tbl_notification
from mainproject.security import hash_password


class AdminRoleAndAccessTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.district = tbl_district.objects.create(district_name="Ernakulam")
        self.place = tbl_place.objects.create(place_name="Kochi", district=self.district)

        # Admin
        self.admin = tbl_adminregistration.objects.create(
            registration_name="Admin",
            registration_email="admin@test.com",
            registration_password=hash_password("admin123")
        )

        # Regular Patient
        self.user = tbl_registration.objects.create(
            registration_name="Patient",
            registration_email="patient@test.com",
            registration_contact="1234567890",
            registration_address="Hospital Road",
            registration_password=hash_password("patient123"),
            place=self.place
        )

        # Doctor
        self.doctor = tbl_doctor.objects.create(
            doctor_name="Doctor",
            doctor_email="doc@test.com",
            doctor_contact="1234567891",
            doctor_password=hash_password("doc123"),
            doctor_status=0,
            place=self.place
        )

        # Shop
        self.shop = tbl_shop.objects.create(
            shop_name="Shop",
            shop_email="shop@test.com",
            shop_contact="1234567892",
            shop_password=hash_password("shop123"),
            shop_status=0,
            place=self.place
        )

    def test_unauthenticated_user_cannot_access_admin_dashboard(self):
        """Unauthenticated visitor is redirected to login."""
        response = self.client.get(reverse('Admin:home'))
        self.assertRedirects(response, reverse('Guest:login'))

    def test_regular_user_cannot_access_admin_pages(self):
        """Patient session cannot access admin pages."""
        session = self.client.session
        session['uid'] = self.user.id
        session['role'] = 'user'
        session.save()

        response = self.client.get(reverse('Admin:home'))
        self.assertRedirects(response, reverse('Guest:login'))

    def test_doctor_cannot_access_admin_pages(self):
        """Doctor session cannot access admin pages."""
        session = self.client.session
        session['did'] = self.doctor.id
        session['role'] = 'doctor'
        session.save()

        response = self.client.get(reverse('Admin:userlist'))
        self.assertRedirects(response, reverse('Guest:login'))

    def test_shop_cannot_access_admin_pages(self):
        """Shop session cannot access admin pages."""
        session = self.client.session
        session['sid'] = self.shop.id
        session['role'] = 'shop'
        session.save()

        response = self.client.get(reverse('Admin:doctorlist'))
        self.assertRedirects(response, reverse('Guest:login'))

    def test_admin_can_approve_doctor(self):
        """Admin can approve a pending doctor."""
        session = self.client.session
        session['aid'] = self.admin.id
        session['role'] = 'admin'
        session.save()

        self.assertEqual(self.doctor.doctor_status, 0)
        response = self.client.post(reverse('Admin:acceptd', args=[self.doctor.id]))
        self.assertRedirects(response, reverse('Admin:doctorlist'))
        self.doctor.refresh_from_db()
        self.assertEqual(self.doctor.doctor_status, 1)

    def test_admin_can_approve_shop(self):
        """Admin can approve a pending shop."""
        session = self.client.session
        session['aid'] = self.admin.id
        session['role'] = 'admin'
        session.save()

        self.assertEqual(self.shop.shop_status, 0)
        response = self.client.post(reverse('Admin:accept', args=[self.shop.id]))
        self.assertRedirects(response, reverse('Admin:shoplist'))
        self.shop.refresh_from_db()
        self.assertEqual(self.shop.shop_status, 1)

    def test_admin_can_reply_to_complaint(self):
        """Admin can reply to a user complaint."""
        complaint = tbl_complaints.objects.create(
            complaints_subject="Late delivery",
            complaints_content="Order took too long",
            user=self.user,
            complaints_status=0
        )
        session = self.client.session
        session['aid'] = self.admin.id
        session['role'] = 'admin'
        session.save()

        response = self.client.post(reverse('Admin:replaycomplaint', args=[complaint.id]), {
            'txtreplay': 'We have expedited your shipment.'
        })
        self.assertRedirects(response, reverse('Admin:usercomplaint'))
        complaint.refresh_from_db()
        self.assertEqual(complaint.complaints_status, 1)
        self.assertEqual(complaint.complaints_reply, 'We have expedited your shipment.')

    def test_admin_approving_doctor_creates_notification_and_audit_log(self):
        """Approving a doctor records an audit log and sends an approval notification."""
        session = self.client.session
        session['aid'] = self.admin.id
        session['role'] = 'admin'
        session.save()

        res = self.client.post(reverse('Admin:acceptd', args=[self.doctor.id]))
        self.assertRedirects(res, reverse('Admin:doctorlist'))

        # Check notification dispatched to doctor
        self.assertTrue(tbl_notification.objects.filter(
            doctor=self.doctor,
            notification_type="system",
            title__icontains="Approved"
        ).exists())

        # Check audit log created
        self.assertTrue(tbl_audit_log.objects.filter(
            action="DOCTOR_APPROVED",
            actor_type="Admin",
            actor_id=self.admin.id,
            details__icontains=self.doctor.doctor_name
        ).exists())

    def test_admin_approving_shop_creates_notification_and_audit_log(self):
        """Approving a shop records an audit log and sends an approval notification."""
        session = self.client.session
        session['aid'] = self.admin.id
        session['role'] = 'admin'
        session.save()

        res = self.client.post(reverse('Admin:accept', args=[self.shop.id]))
        self.assertRedirects(res, reverse('Admin:shoplist'))

        # Check notification dispatched to shop
        self.assertTrue(tbl_notification.objects.filter(
            shop=self.shop,
            notification_type="system",
            title__icontains="Approved"
        ).exists())

        # Check audit log created
        self.assertTrue(tbl_audit_log.objects.filter(
            action="PHARMACY_APPROVED",
            actor_type="Admin",
            actor_id=self.admin.id,
            details__icontains=self.shop.shop_name
        ).exists())

    def test_admin_dashboard_metrics_and_audit_logs(self):
        """Admin dashboard provides system counts and recent audit logs."""
        session = self.client.session
        session['aid'] = self.admin.id
        session['role'] = 'admin'
        session.save()

        # Generate an audit log entry
        tbl_audit_log.objects.create(
            action="SYSTEM_INIT",
            actor_type="System",
            actor_name="System",
            actor_id=0,
            details="System initialization check."
        )

        response = self.client.get(reverse('Admin:home'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('stats', response.context)
        self.assertIn('user_count', response.context['stats'])
        self.assertIn('doctor_count', response.context['stats'])
        self.assertIn('shop_count', response.context['stats'])
        self.assertIn('recent_logs', response.context)
        self.assertGreaterEqual(len(response.context['recent_logs']), 1)

    def test_admin_userlist_pagination(self):
        """Admin user list handles pagination with > 15 users."""
        for i in range(18):
            tbl_registration.objects.create(
                registration_name=f"User {i}",
                registration_email=f"user{i}@example.com",
                registration_contact=f"90000000{i:02d}",
                registration_address="Road St",
                registration_password=hash_password("pw"),
                place=self.place
            )

        session = self.client.session
        session['aid'] = self.admin.id
        session['role'] = 'admin'
        session.save()

        res_p1 = self.client.get(reverse('Admin:userlist'))
        self.assertEqual(res_p1.status_code, 200)
        self.assertEqual(len(res_p1.context['page_obj']), 15)
        self.assertTrue(res_p1.context['page_obj'].has_next())

        res_p2 = self.client.get(reverse('Admin:userlist') + '?page=2')
        self.assertEqual(res_p2.status_code, 200)
        # 1 user from setUp + 18 new = 19 users total -> 15 on p1, 4 on p2
        self.assertEqual(len(res_p2.context['page_obj']), 4)

