import datetime
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from inventory.models import FoodItem, UserProfile


class Command(BaseCommand):
    help = "Safely populate 20 realistic sample food inventory records for demonstration."

    def add_arguments(self, parser):
        parser.add_argument(
            '--username',
            type=str,
            default='greengrocer',
            help="Target business username to own the sample records (default: 'greengrocer')."
        )

    def handle(self, *args, **options):
        target_username = options['username'].strip()
        self.stdout.write(self.style.NOTICE(f"Populating 20 demonstration items for account '{target_username}'..."))

        # 1. Ensure Target Business User Exists
        business_user, created_b = User.objects.get_or_create(
            username=target_username,
            defaults={'email': f'{target_username}@foodsaver.local'}
        )
        if created_b:
            business_user.set_password('DemoPassword123!')
            business_user.save()
            self.stdout.write(self.style.SUCCESS(f"Created demo business account: '{target_username}' (Password: DemoPassword123!)"))

        # Ensure user profile is configured as Business
        profile_b, _ = UserProfile.objects.get_or_create(user=business_user)
        if not profile_b.organization_name:
            profile_b.organization_name = 'Green Valley Supermarket & Deli'
        profile_b.role = 'business'
        if not profile_b.contact_person:
            profile_b.contact_person = 'Marcus Vance'
        if not profile_b.phone:
            profile_b.phone = '+1 555-0144'
        if not profile_b.address:
            profile_b.address = '452 Elm Street, Downtown District'
        profile_b.save()

        # 2. Ensure Demo NGO Partner Exists for complete workflow testing
        ngo_user, created_n = User.objects.get_or_create(
            username='hopekitchen',
            defaults={'email': 'coordinator@hopekitchen.org'}
        )
        if created_n:
            ngo_user.set_password('DemoPassword123!')
            ngo_user.save()
            self.stdout.write(self.style.SUCCESS("Created demo NGO partner: 'hopekitchen' (Password: DemoPassword123!)"))

        profile_n, _ = UserProfile.objects.get_or_create(user=ngo_user)
        profile_n.role = 'ngo'
        if not profile_n.organization_name:
            profile_n.organization_name = 'Hope Community Kitchen & Shelter'
        if not profile_n.contact_person:
            profile_n.contact_person = 'Sarah Jenkins'
        if not profile_n.phone:
            profile_n.phone = '+1 555-0892'
        if not profile_n.address:
            profile_n.address = '108 North Bridge Avenue, Community Center'
        profile_n.save()

        # 3. Define 20 Realistic Demonstration Food Items
        today = timezone.localdate()

        demo_items = [
            # --- CRITICAL (0 to 2 days) ---
            {
                'name': '[Demo] Organic Strawberries',
                'category': 'Produce',
                'quantity': Decimal('8.50'),
                'unit': 'kg',
                'expiry_date': today + datetime.timedelta(days=1), # Critical (1 day)
                'batch_number': 'DEMO-PRD-01',
                'storage_location': 'Cold Room A',
                'description': '[Demonstration Data] Fresh ripe strawberries in 500g punnets. Needs rapid redistribution.',
                'donor_info': 'Green Valley Orchards',
            },
            {
                'name': '[Demo] Fresh Whole Milk (3.2%)',
                'category': 'Dairy',
                'quantity': Decimal('24.00'),
                'unit': 'litres',
                'expiry_date': today + datetime.timedelta(days=1), # Critical (1 day)
                'batch_number': 'DEMO-DRY-02',
                'storage_location': 'Dairy Cooler 1',
                'description': '[Demonstration Data] 1L pasteurized milk cartons. Kept strictly refrigerated at 3°C.',
                'donor_info': 'Sunshine Valley Dairy',
            },
            {
                'name': '[Demo] Artisan Sourdough Batard',
                'category': 'Bakery',
                'quantity': Decimal('12.00'),
                'unit': 'units',
                'expiry_date': today, # Critical (Today)
                'batch_number': 'DEMO-BAK-03',
                'storage_location': 'Bakery Counter Rack',
                'description': '[Demonstration Data] Freshly baked hearth sourdough loaves. Ideal for immediate community kitchen meal service.',
                'donor_info': 'Downtown Hearth Bakery',
            },
            {
                'name': '[Demo] Premium Beef Mince',
                'category': 'Meat',
                'quantity': Decimal('7.50'),
                'unit': 'kg',
                'expiry_date': today + datetime.timedelta(days=2), # Critical (2 days)
                'batch_number': 'DEMO-MEA-04',
                'storage_location': 'Meat Chiller Shelf 2',
                'description': '[Demonstration Data] Vacuum-sealed ground beef cuts. High protein surplus.',
                'donor_info': 'Metro Butchery & Co',
            },
            {
                'name': '[Demo] Atlantic Salmon Portions',
                'category': 'Seafood',
                'quantity': Decimal('5.00'),
                'unit': 'kg',
                'expiry_date': today, # Critical (Today)
                'batch_number': 'DEMO-SEA-05',
                'storage_location': 'Fish Ice Storage',
                'description': '[Demonstration Data] Fresh chilled boneless salmon fillets. Critical shelf life, consume or cook today.',
                'donor_info': 'Harbor Seafood Market',
            },
            {
                'name': '[Demo] Caesar Chicken Salad Bowls',
                'category': 'Prepared Meals',
                'quantity': Decimal('15.00'),
                'unit': 'portions',
                'expiry_date': today + datetime.timedelta(days=1), # Critical (1 day)
                'batch_number': 'DEMO-PREP-06',
                'storage_location': 'Deli Display Fridge',
                'description': '[Demonstration Data] Pre-packaged gourmet chicken caesar salads with dressing separate.',
                'donor_info': 'City Central Deli',
            },

            # --- MEDIUM (3 to 7 days) ---
            {
                'name': '[Demo] Ripe Cavendish Bananas',
                'category': 'Produce',
                'quantity': Decimal('18.00'),
                'unit': 'kg',
                'expiry_date': today + datetime.timedelta(days=3), # Medium (3 days)
                'batch_number': 'DEMO-PRD-07',
                'storage_location': 'Produce Dry Stand 2',
                'description': '[Demonstration Data] Sweet table bananas showing sugar spots. Great for smoothies and community baking.',
                'donor_info': 'Green Valley Supermarket',
            },
            {
                'name': '[Demo] Greek Style Natural Yogurt',
                'category': 'Dairy',
                'quantity': Decimal('16.00'),
                'unit': 'units',
                'expiry_date': today + datetime.timedelta(days=4), # Medium (4 days)
                'batch_number': 'DEMO-DRY-08',
                'storage_location': 'Dairy Cooler 2',
                'description': '[Demonstration Data] 500g tubs of natural thick strained yogurt. Sealed factory tamper-evident lids.',
                'donor_info': 'Sunshine Valley Dairy',
            },
            {
                'name': '[Demo] Whole Wheat Sandwich Bread',
                'category': 'Bakery',
                'quantity': Decimal('20.00'),
                'unit': 'units',
                'expiry_date': today + datetime.timedelta(days=3), # Medium (3 days)
                'batch_number': 'DEMO-BAK-09',
                'storage_location': 'Bakery Stacking Tray',
                'description': '[Demonstration Data] Sliced sandwich loaves with intact packaging.',
                'donor_info': 'Golden Crust Bakes',
            },
            {
                'name': '[Demo] Free-Range Chicken Thighs',
                'category': 'Meat',
                'quantity': Decimal('9.00'),
                'unit': 'kg',
                'expiry_date': today + datetime.timedelta(days=4), # Medium (4 days)
                'batch_number': 'DEMO-MEA-10',
                'storage_location': 'Meat Chiller Shelf 1',
                'description': '[Demonstration Data] Fresh skinless chicken thighs in thermoform packs.',
                'donor_info': 'Green Pastures Farm',
            },
            {
                'name': '[Demo] Vegetable Stir-Fry Kits',
                'category': 'Prepared Meals',
                'quantity': Decimal('10.00'),
                'unit': 'packs',
                'expiry_date': today + datetime.timedelta(days=5), # Medium (5 days)
                'batch_number': 'DEMO-PREP-11',
                'storage_location': 'Chiller Section 3',
                'description': '[Demonstration Data] Pre-washed chopped broccoli, bell peppers, snow peas, and carrots.',
                'donor_info': 'City Central Deli',
            },
            {
                'name': '[Demo] Fresh Squeezed Orange Juice',
                'category': 'Beverages',
                'quantity': Decimal('14.00'),
                'unit': 'litres',
                'expiry_date': today + datetime.timedelta(days=6), # Medium (6 days)
                'batch_number': 'DEMO-BEV-12',
                'storage_location': 'Juice Cooler B',
                'description': '[Demonstration Data] 100% pure cold-pressed citrus juice bottles (1L). Keep refrigerated.',
                'donor_info': 'Orchard Fresh Drinks',
            },

            # --- EXPIRED (< 0 days) ---
            {
                'name': '[Demo] Organic Baby Spinach',
                'category': 'Produce',
                'quantity': Decimal('6.00'),
                'unit': 'packs',
                'expiry_date': today - datetime.timedelta(days=1), # Expired (-1 day)
                'batch_number': 'DEMO-PRD-13',
                'storage_location': 'Chiller 4',
                'description': '[Demonstration Data] Expired yesterday. Retained for composting and waste audit demonstration.',
                'donor_info': 'Green Valley Orchards',
            },
            {
                'name': '[Demo] Fresh Ricotta Cheese',
                'category': 'Dairy',
                'quantity': Decimal('4.00'),
                'unit': 'units',
                'expiry_date': today - datetime.timedelta(days=2), # Expired (-2 days)
                'batch_number': 'DEMO-DRY-14',
                'storage_location': 'Dairy Returns Shelf',
                'description': '[Demonstration Data] Reached expiration 2 days ago. Retained for loss-logging audit records.',
                'donor_info': 'Sunshine Valley Dairy',
            },
            {
                'name': '[Demo] Butter Croissants (6-pack)',
                'category': 'Bakery',
                'quantity': Decimal('5.00'),
                'unit': 'boxes',
                'expiry_date': today - datetime.timedelta(days=1), # Expired (-1 day)
                'batch_number': 'DEMO-BAK-15',
                'storage_location': 'Bakery Returns Rack',
                'description': '[Demonstration Data] Past shelf life date. Demonstration record for expired inventory filter.',
                'donor_info': 'Downtown Hearth Bakery',
            },

            # --- LOW RISK (> 7 days) ---
            {
                'name': '[Demo] Yellowfin Tuna Steaks',
                'category': 'Seafood',
                'quantity': Decimal('8.00'),
                'unit': 'kg',
                'expiry_date': today + datetime.timedelta(days=10), # Low (10 days)
                'batch_number': 'DEMO-SEA-16',
                'storage_location': 'Deep Freezer -18C',
                'description': '[Demonstration Data] Flash-frozen sashimi-grade tuna loins. Long remaining frozen shelf life.',
                'donor_info': 'Oceanic Imports',
            },
            {
                'name': '[Demo] Italian Chopped Tomatoes',
                'category': 'Pantry',
                'quantity': Decimal('48.00'),
                'unit': 'cans',
                'expiry_date': today + datetime.timedelta(days=180), # Low (180 days)
                'batch_number': 'DEMO-PAN-17',
                'storage_location': 'Pantry Aisle 4',
                'description': '[Demonstration Data] 400g canned tomatoes in juice. Stable long-term non-perishable pantry reserve.',
                'donor_info': 'Global Pantry Supply',
            },
            {
                'name': '[Demo] Dried Green Lentils',
                'category': 'Pantry',
                'quantity': Decimal('25.00'),
                'unit': 'kg',
                'expiry_date': today + datetime.timedelta(days=365), # Low (365 days)
                'batch_number': 'DEMO-PAN-18',
                'storage_location': 'Dry Grains Bin 1',
                'description': '[Demonstration Data] High-protein dry bulk pulses in sealed multi-ply kraft sacks.',
                'donor_info': 'Global Pantry Supply',
            },
            {
                'name': '[Demo] Organic Cold Brew Coffee',
                'category': 'Beverages',
                'quantity': Decimal('24.00'),
                'unit': 'units',
                'expiry_date': today + datetime.timedelta(days=21), # Low (21 days)
                'batch_number': 'DEMO-BEV-19',
                'storage_location': 'Dry Beverage Shelf',
                'description': '[Demonstration Data] 330ml ready-to-drink nitro cold brew cans. Ambient storage suitable.',
                'donor_info': 'Artisan Roasters',
            },
            {
                'name': '[Demo] Smoked Turkey Breast Cold Cuts',
                'category': 'Meat',
                'quantity': Decimal('12.00'),
                'unit': 'packs',
                'expiry_date': today + datetime.timedelta(days=12), # Low (12 days)
                'batch_number': 'DEMO-MEA-20',
                'storage_location': 'Meat Chiller Shelf 4',
                'description': '[Demonstration Data] 200g vacuum-sealed sliced deli turkey breast. Sealed factory barrier pouches.',
                'donor_info': 'Metro Butchery & Co',
            },
        ]

        # 4. Idempotently Insert or Update Items
        created_count = 0
        updated_count = 0

        for item_data in demo_items:
            item, created = FoodItem.objects.update_or_create(
                name=item_data['name'],
                added_by=business_user,
                defaults={**item_data, 'added_by': business_user}
            )
            if created:
                created_count += 1
            else:
                updated_count += 1

        total_owned = FoodItem.objects.filter(added_by=business_user).count()

        self.stdout.write(self.style.SUCCESS(
            f"\n[DONE] Demonstration dataset synchronized successfully!\n"
            f"  - Newly Created: {created_count} items\n"
            f"  - Verified/Updated: {updated_count} items\n"
            f"  - Total Items for '{target_username}': {total_owned}\n"
            f"\nDemo Credentials:\n"
            f"  Business Account: '{target_username}' / Password: 'DemoPassword123!' (Access: http://127.0.0.1:8000/)\n"
            f"  NGO Partner Account: 'hopekitchen' / Password: 'DemoPassword123!' (Access: http://127.0.0.1:8000/ngo/dashboard/)"
        ))
