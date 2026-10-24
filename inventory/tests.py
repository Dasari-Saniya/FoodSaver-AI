import datetime
import io
from decimal import Decimal
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone

from .models import FoodItem, UserProfile
from .csv_utils import process_csv_file


class AuthenticationAndRoleTests(TestCase):
    def setUp(self):
        self.client = Client()

    def test_business_user_registration(self):
        response = self.client.post(reverse('register'), {
            'username': 'bakery_owner',
            'email': 'owner@artisanbakery.com',
            'role': 'business',
            'organization_name': 'Artisan Sourdough Bakery',
            'contact_person': 'Oliver Twist',
            'phone': '+1 555-0100',
            'address': '12 Baker Street',
            'password1': 'SecurePass123!',
            'password2': 'SecurePass123!',
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(User.objects.filter(username='bakery_owner').exists())
        user = User.objects.get(username='bakery_owner')
        # Check security: hashed password, not staff, not superuser
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertNotEqual(user.password, 'SecurePass123!')
        self.assertTrue(user.check_password('SecurePass123!'))
        user.profile.refresh_from_db()
        self.assertEqual(user.profile.role, 'business')
        self.assertEqual(user.profile.organization_name, 'Artisan Sourdough Bakery')

    def test_ngo_user_registration(self):
        response = self.client.post(reverse('register'), {
            'username': 'community_kitchen',
            'email': 'help@communitykitchen.org',
            'role': 'ngo',
            'organization_name': 'Downtown Community Food Bank',
            'contact_person': 'Elena Rostova',
            'phone': '+1 555-0200',
            'address': '45 Harbor Road',
            'password1': 'SecurePass123!',
            'password2': 'SecurePass123!',
        })
        self.assertEqual(response.status_code, 302)
        user = User.objects.get(username='community_kitchen')
        user.profile.refresh_from_db()
        self.assertEqual(user.profile.role, 'ngo')
        self.assertTrue(user.profile.is_ngo)
        self.assertFalse(user.profile.is_business)

    def test_login_and_logout(self):
        user = User.objects.create_user(username='loginuser', password='Password123!', email='user@test.com')
        user.profile.role = 'business'
        user.profile.organization_name = 'Test Shop'
        user.profile.save()

        login_res = self.client.post(reverse('login'), {
            'username': 'loginuser',
            'password': 'Password123!',
        })
        self.assertEqual(login_res.status_code, 302)

        logout_res = self.client.get(reverse('logout'))
        self.assertEqual(logout_res.status_code, 302)
        self.assertRedirects(logout_res, reverse('login'))


class OwnershipIsolationTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.today = timezone.localdate()

        # Business User 1
        self.user1 = User.objects.create_user(username='business1', password='Password123!')
        self.user1.profile.role = 'business'
        self.user1.profile.organization_name = 'Business One'
        self.user1.profile.save()

        # Business User 2
        self.user2 = User.objects.create_user(username='business2', password='Password123!')
        self.user2.profile.role = 'business'
        self.user2.profile.organization_name = 'Business Two'
        self.user2.profile.save()

        # Items
        self.item1 = FoodItem.objects.create(
            name='User1 Apples',
            category='Produce',
            quantity=Decimal('10.00'),
            unit='kg',
            expiry_date=self.today + datetime.timedelta(days=3),
            added_by=self.user1
        )
        self.item2 = FoodItem.objects.create(
            name='User2 Bread',
            category='Bakery',
            quantity=Decimal('5.00'),
            unit='units',
            expiry_date=self.today + datetime.timedelta(days=2),
            added_by=self.user2
        )

    def test_business_only_sees_own_inventory(self):
        self.client.login(username='business1', password='Password123!')
        response = self.client.get(reverse('inventory_list'))
        self.assertContains(response, 'User1 Apples')
        self.assertNotContains(response, 'User2 Bread')

    def test_user_cannot_edit_other_users_item(self):
        self.client.login(username='business1', password='Password123!')
        # Try to edit User 2's item -> Should be HTTP 403 Forbidden
        response = self.client.get(reverse('food_update', args=[self.item2.pk]))
        self.assertEqual(response.status_code, 403)

    def test_user_cannot_delete_other_users_item(self):
        self.client.login(username='business1', password='Password123!')
        # Try to delete User 2's item -> Should be HTTP 403 Forbidden
        response = self.client.post(reverse('food_delete', args=[self.item2.pk]))
        self.assertEqual(response.status_code, 403)
        self.assertTrue(FoodItem.objects.filter(pk=self.item2.pk).exists())


class NGOPortalTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.today = timezone.localdate()

        self.business_user = User.objects.create_user(username='market', password='Password123!')
        self.business_user.profile.role = 'business'
        self.business_user.profile.organization_name = 'Market Co'
        self.business_user.profile.save()

        self.ngo_user = User.objects.create_user(username='food_bank', password='Password123!')
        self.ngo_user.profile.role = 'ngo'
        self.ngo_user.profile.organization_name = 'City Food Bank'
        self.ngo_user.profile.save()

        # Active surplus item
        self.surplus_item = FoodItem.objects.create(
            name='Surplus Milk',
            category='Dairy',
            quantity=Decimal('20.00'),
            unit='litres',
            expiry_date=self.today + datetime.timedelta(days=1),
            donor_info='Market Co',
            added_by=self.business_user
        )

        # Expired item (should not show on NGO active surplus)
        self.expired_item = FoodItem.objects.create(
            name='Expired Cereal',
            category='Pantry',
            quantity=Decimal('2.00'),
            unit='boxes',
            expiry_date=self.today - datetime.timedelta(days=1),
            donor_info='Market Co',
            added_by=self.business_user
        )

    def test_ngo_sees_active_surplus_across_providers(self):
        self.client.login(username='food_bank', password='Password123!')
        response = self.client.get(reverse('ngo_dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Surplus Milk')
        self.assertNotContains(response, 'Expired Cereal')

    def test_ngo_redirected_from_inventory_creation(self):
        self.client.login(username='food_bank', password='Password123!')
        response = self.client.get(reverse('food_create'))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('ngo_dashboard'))


class ExpiryBoundaryAndWasteRiskTests(TestCase):
    def setUp(self):
        self.today = timezone.localdate()

    def test_expiry_boundaries(self):
        # 1. Past date -> EXPIRED
        expired = FoodItem(name='Item', category='Produce', quantity=Decimal('1'), expiry_date=self.today - datetime.timedelta(days=1))
        self.assertEqual(expired.days_until_expiry, -1)
        self.assertEqual(expired.expiry_status, 'Expired')

        # 2. Today (0 days) -> CRITICAL
        today_item = FoodItem(name='Item', category='Produce', quantity=Decimal('1'), expiry_date=self.today)
        self.assertEqual(today_item.days_until_expiry, 0)
        self.assertEqual(today_item.expiry_status, 'Critical')

        # 3. Exactly 2 days -> CRITICAL
        two_days = FoodItem(name='Item', category='Produce', quantity=Decimal('1'), expiry_date=self.today + datetime.timedelta(days=2))
        self.assertEqual(two_days.days_until_expiry, 2)
        self.assertEqual(two_days.expiry_status, 'Critical')

        # 4. Exactly 3 days -> MEDIUM
        three_days = FoodItem(name='Item', category='Produce', quantity=Decimal('1'), expiry_date=self.today + datetime.timedelta(days=3))
        self.assertEqual(three_days.days_until_expiry, 3)
        self.assertEqual(three_days.expiry_status, 'Medium')

        # 5. Exactly 7 days -> MEDIUM
        seven_days = FoodItem(name='Item', category='Produce', quantity=Decimal('1'), expiry_date=self.today + datetime.timedelta(days=7))
        self.assertEqual(seven_days.days_until_expiry, 7)
        self.assertEqual(seven_days.expiry_status, 'Medium')

        # 6. Exactly 8 days -> LOW
        eight_days = FoodItem(name='Item', category='Produce', quantity=Decimal('1'), expiry_date=self.today + datetime.timedelta(days=8))
        self.assertEqual(eight_days.days_until_expiry, 8)
        self.assertEqual(eight_days.expiry_status, 'Low')

    def test_waste_risk_score_calculation(self):
        # Expired item carries 100% loss risk
        expired = FoodItem(name='Milk', category='Dairy', quantity=Decimal('1'), expiry_date=self.today - datetime.timedelta(days=1))
        self.assertEqual(expired.waste_risk_score, 100)
        self.assertEqual(expired.waste_risk_level, 'High Risk')

        # Today critical item carries 95% risk
        crit = FoodItem(name='Milk', category='Dairy', quantity=Decimal('1'), expiry_date=self.today)
        self.assertGreaterEqual(crit.waste_risk_score, 85)
        self.assertEqual(crit.waste_risk_level, 'High Risk')

        # Distant low risk item
        low = FoodItem(name='Canned', category='Pantry', quantity=Decimal('1'), expiry_date=self.today + datetime.timedelta(days=60))
        self.assertLessEqual(low.waste_risk_score, 30)
        self.assertEqual(low.waste_risk_level, 'Low Risk')


class CSVImportAndValidationTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='csvowner', password='Password123!')
        self.user.profile.role = 'business'
        self.user.profile.organization_name = 'CSV Testing Co'
        self.user.profile.save()
        self.client.login(username='csvowner', password='Password123!')
        self.today = timezone.localdate()

    def test_csv_import_with_tracking_fields_and_owner_attribution(self):
        csv_data = (
            "food_name,category,quantity,unit,expiry_date,batch_number,storage_location\n"
            f"Greek Yogurt,Dairy,10.00,units,{self.today + datetime.timedelta(days=1)},BATCH-YOG-1,Chiller A\n"
            f"Whole Wheat Loaf,Bakery,15.00,units,{self.today + datetime.timedelta(days=3)},BATCH-BREAD-2,Rack 4\n"
        ).encode('utf-8')

        file_obj = io.BytesIO(csv_data)
        result = process_csv_file(file_obj, user=self.user)

        self.assertEqual(result['success_count'], 2)
        self.assertEqual(result['failed_count'], 0)

        item = FoodItem.objects.get(name='Greek Yogurt')
        self.assertEqual(item.added_by, self.user)
        self.assertEqual(item.batch_number, 'BATCH-YOG-1')
        self.assertEqual(item.storage_location, 'Chiller A')

    def test_csv_import_graceful_row_failures(self):
        csv_data = (
            "food_name,category,quantity,unit,expiry_date\n"
            f"Good Item,Produce,5,kg,{self.today + datetime.timedelta(days=4)}\n"
            f"Bad Negative Qty,Produce,-2,kg,{self.today + datetime.timedelta(days=4)}\n"
            "Bad Empty Date,Produce,10,kg,\n"
            f",Produce,3,kg,{self.today + datetime.timedelta(days=4)}\n"
        ).encode('utf-8')

        file_obj = io.BytesIO(csv_data)
        result = process_csv_file(file_obj, user=self.user)

        self.assertEqual(result['success_count'], 1)
        self.assertEqual(result['failed_count'], 3)
        self.assertEqual(len(result['errors']), 3)

    def test_sample_csv_download_endpoint(self):
        response = self.client.get(reverse('download_sample_csv'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/csv')


class InventoryCRUDAndSearchTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='chef_mario', password='Password123!')
        self.user.profile.role = 'business'
        self.user.profile.organization_name = 'Mario Trattoria'
        self.user.profile.save()
        self.client.login(username='chef_mario', password='Password123!')
        self.today = timezone.localdate()

        self.item = FoodItem.objects.create(
            name='San Marzano Tomatoes',
            category='Pantry',
            quantity=Decimal('24.00'),
            unit='cans',
            expiry_date=self.today + datetime.timedelta(days=120),
            batch_number='LOT-TOM-99',
            storage_location='Dry Storage Shelf 2',
            donor_info='Mario Trattoria',
            added_by=self.user
        )

    def test_create_food_item(self):
        create_url = reverse('food_create')
        post_data = {
            'name': 'Fresh Mozzarella',
            'category': 'Dairy',
            'quantity': '10.00',
            'unit': 'units',
            'expiry_date': (self.today + datetime.timedelta(days=2)).strftime('%Y-%m-%d'),
            'batch_number': 'LOT-MOZ-1',
            'storage_location': 'Cheese Fridge',
            'donor_info': 'Mario Trattoria',
            'description': 'Keep refrigerated at 4 degrees.',
        }
        response = self.client.post(create_url, post_data)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(FoodItem.objects.filter(name='Fresh Mozzarella').exists())
        mozz = FoodItem.objects.get(name='Fresh Mozzarella')
        self.assertEqual(mozz.added_by, self.user)
        self.assertEqual(mozz.expiry_status, 'Critical')

    def test_view_food_detail(self):
        url = reverse('food_detail', args=[self.item.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'San Marzano Tomatoes')
        self.assertContains(response, 'LOT-TOM-99')
        self.assertContains(response, 'Dry Storage Shelf 2')

    def test_update_food_item(self):
        url = reverse('food_update', args=[self.item.pk])
        post_data = {
            'name': 'San Marzano Tomatoes (Updated)',
            'category': 'Pantry',
            'quantity': '30.00',
            'unit': 'cans',
            'expiry_date': self.item.expiry_date.strftime('%Y-%m-%d'),
            'batch_number': 'LOT-TOM-99-REV',
            'storage_location': 'Dry Storage Shelf 3',
            'donor_info': 'Mario Trattoria',
            'description': 'Updated stock count.',
        }
        response = self.client.post(url, post_data)
        self.assertEqual(response.status_code, 302)
        self.item.refresh_from_db()
        self.assertEqual(self.item.name, 'San Marzano Tomatoes (Updated)')
        self.assertEqual(self.item.quantity, Decimal('30.00'))
        self.assertEqual(self.item.batch_number, 'LOT-TOM-99-REV')

    def test_delete_food_item(self):
        url = reverse('food_delete', args=[self.item.pk])
        # GET renders confirmation
        get_res = self.client.get(url)
        self.assertEqual(get_res.status_code, 200)
        self.assertContains(get_res, 'Confirm Item Deletion')

        # POST deletes item
        post_res = self.client.post(url)
        self.assertEqual(post_res.status_code, 302)
        self.assertFalse(FoodItem.objects.filter(pk=self.item.pk).exists())

    def test_search_and_multi_filtering_and_sorting(self):
        FoodItem.objects.create(
            name='Organic Spinach',
            category='Produce',
            quantity=Decimal('5.00'),
            unit='packs',
            expiry_date=self.today + datetime.timedelta(days=1),
            donor_info='Mario Trattoria',
            added_by=self.user
        )

        # Keyword search
        res = self.client.get(reverse('inventory_list'), {'q': 'Spinach'})
        self.assertContains(res, 'Organic Spinach')
        self.assertNotContains(res, 'San Marzano Tomatoes')

        # Category filter
        res = self.client.get(reverse('inventory_list'), {'category': 'Produce'})
        self.assertContains(res, 'Organic Spinach')
        self.assertNotContains(res, 'San Marzano Tomatoes')

        # Expiry status filter
        res = self.client.get(reverse('inventory_list'), {'status': 'Critical'})
        self.assertContains(res, 'Organic Spinach')
        self.assertNotContains(res, 'San Marzano Tomatoes')

        # Combined filter: Category + Status
        res = self.client.get(reverse('inventory_list'), {'category': 'Produce', 'status': 'Critical'})
        self.assertContains(res, 'Organic Spinach')

        # Sorting by name A-Z
        res = self.client.get(reverse('inventory_list'), {'sort_by': 'name'})
        self.assertEqual(res.status_code, 200)


class ProtectedPageAccessTests(TestCase):
    def setUp(self):
        self.client = Client()

    def test_unauthenticated_user_redirected_to_login(self):
        urls = [
            reverse('inventory_list'),
            reverse('food_create'),
            reverse('csv_upload'),
            reverse('ngo_dashboard'),
        ]
        for url in urls:
            res = self.client.get(url)
            self.assertEqual(res.status_code, 302)
            self.assertTrue(res.url.startswith(reverse('login')))

