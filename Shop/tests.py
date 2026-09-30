from decimal import Decimal
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
