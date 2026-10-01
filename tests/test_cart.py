from decimal import Decimal
from django.test import TestCase, Client
from django.urls import reverse
from Admin.models import tbl_district, tbl_place
from Guest.models import tbl_registration, tbl_shop
from Shop.models import tbl_category, tbl_medicine, tbl_stock
from User.models import tbl_booking, tbl_cart
from mainproject.security import hash_password


class CartFunctionalityTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.district = tbl_district.objects.create(district_name="Malappuram")
        self.place = tbl_place.objects.create(place_name="Manjeri", district=self.district)

        self.patient = tbl_registration.objects.create(
            registration_name="Cart User",
            registration_email="cart_user@test.com",
            registration_contact="9876543301",
            registration_address="Manjeri",
            registration_password=hash_password("pw"),
            place=self.place
        )

        self.shop = tbl_shop.objects.create(
            shop_name="Manjeri Meds",
            shop_email="manjeri_shop@test.com",
            shop_contact="9876543302",
            shop_password=hash_password("pw"),
            shop_status=1,
            place=self.place
        )

        self.cat = tbl_category.objects.create(category_name="Pain Relief")

        self.in_stock_med = tbl_medicine.objects.create(
            medicine_name="Ibuprofen 400mg",
            medicine_details="Pain & fever",
            medicine_price=Decimal("30.00"),
            shop=self.shop,
            category=self.cat,
            medicine_status=0
        )
        tbl_stock.objects.create(medicine=self.in_stock_med, stock_qty=10)

        self.out_stock_med = tbl_medicine.objects.create(
            medicine_name="Rare Syrup",
            medicine_details="Out of stock",
            medicine_price=Decimal("150.00"),
            shop=self.shop,
            category=self.cat,
            medicine_status=0
        )
        # 0 stock

    def test_add_to_cart_success_and_duplicate_handling(self):
        """Medicine added to cart, and adding again does not duplicate cart row."""
        session = self.client.session
        session['uid'] = self.patient.id
        session['role'] = 'user'
        session.save()

        # Add first time
        res1 = self.client.get(reverse('User:Addcart', args=[self.in_stock_med.id]))
        self.assertRedirects(res1, reverse('User:Mycart'))
        self.assertEqual(tbl_cart.objects.filter(medicine=self.in_stock_med).count(), 1)

        # Add second time
        res2 = self.client.get(reverse('User:Addcart', args=[self.in_stock_med.id]))
        self.assertRedirects(res2, reverse('User:Mycart'))
        # Still only 1 row
        self.assertEqual(tbl_cart.objects.filter(medicine=self.in_stock_med).count(), 1)

    def test_out_of_stock_cannot_be_added(self):
        """Attempting to add out of stock medicine is rejected with error."""
        session = self.client.session
        session['uid'] = self.patient.id
        session['role'] = 'user'
        session.save()

        res = self.client.get(reverse('User:Addcart', args=[self.out_stock_med.id]))
        self.assertRedirects(res, reverse('User:viewmedicine', args=[self.shop.id]))
        self.assertFalse(tbl_cart.objects.filter(medicine=self.out_stock_med).exists())

    def test_cart_quantity_clamped_to_available_stock(self):
        """Updating quantity beyond available stock clamps quantity to available maximum."""
        session = self.client.session
        session['uid'] = self.patient.id
        session['role'] = 'user'
        session.save()

        self.client.get(reverse('User:Addcart', args=[self.in_stock_med.id]))
        cart_item = tbl_cart.objects.get(medicine=self.in_stock_med)

        # Try to set quantity to 99 when stock is 10
        self.client.post(reverse('User:cartqty'), {'ALT': cart_item.id, 'QTY': 99})
        cart_item.refresh_from_db()
        self.assertEqual(cart_item.cart_quantity, 10)

    def test_cart_quantity_invalid_value_normalized(self):
        """Invalid or negative quantity defaults to minimum 1."""
        session = self.client.session
        session['uid'] = self.patient.id
        session['role'] = 'user'
        session.save()

        self.client.get(reverse('User:Addcart', args=[self.in_stock_med.id]))
        cart_item = tbl_cart.objects.get(medicine=self.in_stock_med)

        # Negative quantity
        self.client.post(reverse('User:cartqty'), {'ALT': cart_item.id, 'QTY': -5})
        cart_item.refresh_from_db()
        self.assertEqual(cart_item.cart_quantity, 1)

        # Non-numeric quantity
        self.client.post(reverse('User:cartqty'), {'ALT': cart_item.id, 'QTY': 'invalid_string'})
        cart_item.refresh_from_db()
        self.assertEqual(cart_item.cart_quantity, 1)

    def test_delcart_requires_post(self):
        """DelCart endpoint requires POST request; GET request is rejected with 405."""
        session = self.client.session
        session['uid'] = self.patient.id
        session['role'] = 'user'
        session.save()

        self.client.get(reverse('User:Addcart', args=[self.in_stock_med.id]))
        cart_item = tbl_cart.objects.get(medicine=self.in_stock_med)

        # Attempt GET request
        res_get = self.client.get(reverse('User:delcart', args=[cart_item.id]))
        self.assertEqual(res_get.status_code, 405)
        self.assertTrue(tbl_cart.objects.filter(id=cart_item.id).exists())

        # Attempt POST request
        res_post = self.client.post(reverse('User:delcart', args=[cart_item.id]))
        self.assertRedirects(res_post, reverse('User:Mycart'))
        self.assertFalse(tbl_cart.objects.filter(id=cart_item.id).exists())
