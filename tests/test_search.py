from decimal import Decimal
from django.test import TestCase, Client
from django.urls import reverse
from Admin.models import tbl_district, tbl_place
from Guest.models import tbl_registration, tbl_shop
from Shop.models import tbl_category, tbl_medicine, tbl_stock
from mainproject.security import hash_password


class MedicineSearchAndFilterTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.district = tbl_district.objects.create(district_name="Kasaragod")
        self.place = tbl_place.objects.create(place_name="Kanhangad", district=self.district)

        self.patient = tbl_registration.objects.create(
            registration_name="Search User",
            registration_email="search_user@test.com",
            registration_contact="9876543701",
            registration_address="Kanhangad",
            registration_password=hash_password("pw"),
            place=self.place
        )

        self.shop1 = tbl_shop.objects.create(
            shop_name="Kanhangad Pharmacy",
            shop_email="kanhangad_shop@test.com",
            shop_contact="9876543702",
            shop_password=hash_password("pw"),
            shop_status=1,
            place=self.place
        )

        self.shop2 = tbl_shop.objects.create(
            shop_name="Metro Pharmacy",
            shop_email="metro_shop@test.com",
            shop_contact="9876543703",
            shop_password=hash_password("pw"),
            shop_status=1,
            place=self.place
        )

        self.cat_analgesic = tbl_category.objects.create(category_name="Analgesics")
        self.cat_derma = tbl_category.objects.create(category_name="Dermatology")

        # In-stock OTC medicine at shop1
        self.med1 = tbl_medicine.objects.create(
            medicine_name="Paracetamol 650mg",
            medicine_details="Relief for fever and pain",
            medicine_price=Decimal("25.00"),
            shop=self.shop1,
            category=self.cat_analgesic,
            medicine_status=0  # OTC
        )
        tbl_stock.objects.create(medicine=self.med1, stock_qty=50)

        # In-stock Rx medicine at shop1
        self.med2 = tbl_medicine.objects.create(
            medicine_name="Tramadol 50mg",
            medicine_details="Severe pain",
            medicine_price=Decimal("95.00"),
            shop=self.shop1,
            category=self.cat_analgesic,
            medicine_status=1  # Rx
        )
        tbl_stock.objects.create(medicine=self.med2, stock_qty=20)

        # Out-of-stock OTC medicine at shop2
        self.med3 = tbl_medicine.objects.create(
            medicine_name="Hydrocortisone Cream",
            medicine_details="Skin soothing cream",
            medicine_price=Decimal("60.00"),
            shop=self.shop2,
            category=self.cat_derma,
            medicine_status=0  # OTC
        )
        # 0 stock

    def test_case_insensitive_partial_search(self):
        """Search query matches case-insensitively on name and details."""
        session = self.client.session
        session['uid'] = self.patient.id
        session['role'] = 'user'
        session.save()

        # Partial lowercase search 'para'
        res = self.client.get(reverse('User:search') + '?q=para')
        self.assertEqual(res.status_code, 200)
        names = [m.medicine_name for m in res.context['med']]
        self.assertIn("Paracetamol 650mg", names)
        self.assertNotIn("Hydrocortisone Cream", names)

        # Search by detail keyword 'fever'
        res_detail = self.client.get(reverse('User:search') + '?q=fever')
        self.assertEqual(res_detail.status_code, 200)
        names_detail = [m.medicine_name for m in res_detail.context['med']]
        self.assertIn("Paracetamol 650mg", names_detail)

    def test_filter_by_shop(self):
        """Filter by shop ID only returns medicines belonging to that pharmacy."""
        session = self.client.session
        session['uid'] = self.patient.id
        session['role'] = 'user'
        session.save()

        res = self.client.get(reverse('User:search') + f'?shop={self.shop2.id}')
        self.assertEqual(res.status_code, 200)
        for m in res.context['med']:
            self.assertEqual(m.shop_id, self.shop2.id)

    def test_filter_by_availability_in_stock(self):
        """Availability filter 'in_stock' excludes medicines with zero available stock."""
        session = self.client.session
        session['uid'] = self.patient.id
        session['role'] = 'user'
        session.save()

        res = self.client.get(reverse('User:search') + '?availability=in_stock')
        self.assertEqual(res.status_code, 200)
        names = [m.medicine_name for m in res.context['med']]
        self.assertIn("Paracetamol 650mg", names)
        self.assertIn("Tramadol 50mg", names)
        self.assertNotIn("Hydrocortisone Cream", names)

    def test_sorting_by_price(self):
        """Sorting parameters order medicines correctly."""
        session = self.client.session
        session['uid'] = self.patient.id
        session['role'] = 'user'
        session.save()

        # Price ascending
        res_asc = self.client.get(reverse('User:search') + '?sort=price_asc')
        self.assertEqual(res_asc.status_code, 200)
        prices = [m.medicine_price for m in res_asc.context['med']]
        self.assertEqual(prices, sorted(prices))

        # Price descending
        res_desc = self.client.get(reverse('User:search') + '?sort=price_desc')
        self.assertEqual(res_desc.status_code, 200)
        prices_desc = [m.medicine_price for m in res_desc.context['med']]
        self.assertEqual(prices_desc, sorted(prices_desc, reverse=True))
