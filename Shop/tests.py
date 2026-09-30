from decimal import Decimal
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, Client
from django.urls import reverse
from Admin.models import tbl_district, tbl_place
from Guest.models import tbl_registration, tbl_shop
from Shop.models import tbl_category, tbl_medicine, tbl_stock
from User.models import tbl_booking, tbl_cart
from mainproject.security import hash_password


class ShopSecurityAndManagementTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.district = tbl_district.objects.create(district_name="Palakkad")
        self.place = tbl_place.objects.create(place_name="Ottapalam", district=self.district)

        self.category = tbl_category.objects.create(category_name="Pain Relief")

        self.shop1 = tbl_shop.objects.create(
            shop_name="Care Pharmacy",
            shop_email="care@pharmacy.com",
            shop_contact="1234567890",
            shop_address="Care Street",
            shop_password=hash_password("shoppass"),
            shop_status=1,
            place=self.place
        )

        self.shop2 = tbl_shop.objects.create(
            shop_name="MediLife Pharmacy",
            shop_email="medilife@pharmacy.com",
            shop_contact="1234567891",
            shop_password=hash_password("shoppass"),
            shop_status=1,
            place=self.place
        )

        self.med1 = tbl_medicine.objects.create(
            medicine_name="Paracetamol 500mg",
            medicine_details="Pain relief",
            medicine_price=Decimal("15.50"),
            shop=self.shop1,
            category=self.category,
            medicine_status=0
        )

        self.med2 = tbl_medicine.objects.create(
            medicine_name="Amoxicillin 250mg",
            medicine_details="Antibiotic",
            medicine_price=Decimal("45.00"),
            shop=self.shop2,
            category=self.category,
            medicine_status=1
        )

    def test_shop_cannot_delete_another_shops_medicine(self):
        """Shop 1 cannot delete Shop 2's medicine (IDOR prevention)."""
        session = self.client.session
        session['sid'] = self.shop1.id
        session['role'] = 'shop'
        session.save()

        # Shop 1 attempts to delete Shop 2's medicine
        response = self.client.post(reverse('Shop:deletemed', args=[self.med2.id]))
        self.assertEqual(response.status_code, 404)
        self.assertTrue(tbl_medicine.objects.filter(id=self.med2.id).exists())

    def test_shop_cannot_add_stock_to_another_shops_medicine(self):
        """Shop 1 cannot add stock to Shop 2's medicine."""
        session = self.client.session
        session['sid'] = self.shop1.id
        session['role'] = 'shop'
        session.save()

        response = self.client.post(reverse('Shop:addstock', args=[self.med2.id]), {
            'stock_qty': '50'
        })
        self.assertEqual(response.status_code, 404)

    def test_shop_can_add_stock_to_own_medicine(self):
        """Shop 1 successfully adds stock to its own medicine."""
        session = self.client.session
        session['sid'] = self.shop1.id
        session['role'] = 'shop'
        session.save()

        response = self.client.post(reverse('Shop:addstock', args=[self.med1.id]), {
            'stock_qty': '25'
        })
        self.assertRedirects(response, reverse('Shop:medicine'))
        self.assertTrue(tbl_stock.objects.filter(medicine=self.med1, stock_qty=25).exists())

    def test_shop_order_isolation(self):
        """Shop 1 only sees bookings containing items from Shop 1."""
        user = tbl_registration.objects.create(
            registration_name="Bob",
            registration_email="bob@test.com",
            registration_contact="9999999999",
            registration_address="Bob St",
            registration_password=hash_password("bobpass"),
            place=self.place
        )

        booking_shop2 = tbl_booking.objects.create(
            user=user,
            booking_amount=Decimal("45.00"),
            booking_status=2
        )
        tbl_cart.objects.create(
            booking=booking_shop2,
            medicine=self.med2,
            cart_quantity=1,
            cart_status=1,
            unit_price=Decimal("45.00")
        )

        session = self.client.session
        session['sid'] = self.shop1.id
        session['role'] = 'shop'
        session.save()

        response = self.client.get(reverse('Shop:booking'))
        self.assertEqual(response.status_code, 200)
        # Booking for Shop 2 should NOT appear in Shop 1's bookings list
        self.assertNotIn(booking_shop2, response.context['booking'])

    def test_shop_order_status_transitions(self):
        """Shop can only transition order status from 2 -> 3 (packing) and 3 -> 4 (delivery)."""
        user = tbl_registration.objects.create(
            registration_name="Alice",
            registration_email="alice@test.com",
            registration_contact="9876543210",
            registration_address="Alice St",
            registration_password=hash_password("alicepass"),
            place=self.place
        )

        booking = tbl_booking.objects.create(
            user=user,
            booking_amount=Decimal("15.50"),
            booking_status=2  # Paid
        )
        tbl_cart.objects.create(
            booking=booking,
            medicine=self.med1,
            cart_quantity=1,
            cart_status=1,
            unit_price=Decimal("15.50")
        )

        session = self.client.session
        session['sid'] = self.shop1.id
        session['role'] = 'shop'
        session.save()

        # Invalid transition: attempting delivery directly from status=2 is blocked
        res_invalid = self.client.post(reverse('Shop:delivery', args=[booking.id]))
        self.assertRedirects(res_invalid, reverse('Shop:booking'))
        booking.refresh_from_db()
        self.assertEqual(booking.booking_status, 2)

        # Valid transition: packing (2 -> 3)
        res_pack = self.client.post(reverse('Shop:packing', args=[booking.id]))
        self.assertRedirects(res_pack, reverse('Shop:booking'))
        booking.refresh_from_db()
        self.assertEqual(booking.booking_status, 3)

        # Invalid transition: calling packing again when status=3 is blocked
        res_pack_again = self.client.post(reverse('Shop:packing', args=[booking.id]))
        self.assertRedirects(res_pack_again, reverse('Shop:booking'))
        booking.refresh_from_db()
        self.assertEqual(booking.booking_status, 3)

        # Valid transition: delivery (3 -> 4)
        res_del = self.client.post(reverse('Shop:delivery', args=[booking.id]))
        self.assertRedirects(res_del, reverse('Shop:booking'))
        booking.refresh_from_db()
        self.assertEqual(booking.booking_status, 4)

    def test_shop_cannot_add_medicine_with_negative_price(self):
        """Server-side validation rejects negative medicine price."""
        session = self.client.session
        session['sid'] = self.shop1.id
        session['role'] = 'shop'
        session.save()

        response = self.client.post(reverse('Shop:medicine'), {
            'medname': 'Invalid Med',
            'details': 'Should fail',
            'price': '-50.00',
            'category': self.category.id,
            'rad': 'yes'
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(tbl_medicine.objects.filter(medicine_name='Invalid Med').exists())

    def test_shop_add_medicine_rejects_disallowed_file_type(self):
        """Medicine image upload rejects executable files."""
        session = self.client.session
        session['sid'] = self.shop1.id
        session['role'] = 'shop'
        session.save()

        fake_exe = SimpleUploadedFile("malware.exe", b"MZmaliciouscode", content_type="application/x-msdownload")
        response = self.client.post(reverse('Shop:medicine'), {
            'medname': 'Malware Med',
            'details': 'Disallowed file',
            'price': '30.00',
            'photo': fake_exe,
            'category': self.category.id,
            'rad': 'yes'
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(tbl_medicine.objects.filter(medicine_name='Malware Med').exists())

    def test_shop_add_stock_rejects_negative_or_zero_quantity(self):
        """Shop cannot add zero or negative stock."""
        session = self.client.session
        session['sid'] = self.shop1.id
        session['role'] = 'shop'
        session.save()

        initial_count = tbl_stock.objects.filter(medicine=self.med1).count()

        # Post zero stock
        res_zero = self.client.post(reverse('Shop:addstock', args=[self.med1.id]), {
            'stock_qty': '0'
        })
        self.assertEqual(res_zero.status_code, 200)
        self.assertEqual(tbl_stock.objects.filter(medicine=self.med1).count(), initial_count)

        # Post negative stock
        res_neg = self.client.post(reverse('Shop:addstock', args=[self.med1.id]), {
            'stock_qty': '-10'
        })
        self.assertEqual(res_neg.status_code, 200)
        self.assertEqual(tbl_stock.objects.filter(medicine=self.med1).count(), initial_count)
