import datetime
from decimal import Decimal
from django.conf import settings
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone


def get_expiry_thresholds():
    """Retrieve configurable expiry thresholds from settings."""
    defaults = {'CRITICAL_DAYS': 2, 'MEDIUM_DAYS': 7}
    return getattr(settings, 'EXPIRY_THRESHOLDS', defaults)


class UserProfile(models.Model):
    """
    Extends Django User with role-based access and organization details.
    Roles:
      - business: Food Provider / Donor (supermarket, restaurant, bakery, etc.)
      - ngo: Community Kitchen / NGO / Food Bank (recipient / food rescue)
    """
    ROLE_CHOICES = [
        ('business', 'Business / Food Provider'),
        ('ngo', 'NGO / Community Kitchen'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='business')
    organization_name = models.CharField(max_length=255, blank=True, default="", verbose_name="Organization / Business Name")
    contact_person = models.CharField(max_length=150, blank=True, default="", verbose_name="Contact Person")
    phone = models.CharField(max_length=50, blank=True, default="", verbose_name="Phone Number")
    address = models.TextField(blank=True, default="", verbose_name="Address / Location")

    class Meta:
        verbose_name = "User Profile"
        verbose_name_plural = "User Profiles"

    def __str__(self):
        org = f" ({self.organization_name})" if self.organization_name else ""
        return f"{self.user.username}{org} - {self.get_role_display()}"

    @property
    def is_business(self):
        return self.role == 'business'

    @property
    def is_ngo(self):
        return self.role == 'ngo'


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """Automatically ensure a UserProfile exists for every newly created User."""
    if created:
        UserProfile.objects.get_or_create(user=instance)


class FoodItemQuerySet(models.QuerySet):
    """Custom queryset providing dynamic expiry status filtering at the DB level."""

    def filter_by_status(self, status):
        today = timezone.localdate()
        thresholds = get_expiry_thresholds()
        crit_days = thresholds.get('CRITICAL_DAYS', 2)
        med_days = thresholds.get('MEDIUM_DAYS', 7)

        crit_limit = today + datetime.timedelta(days=crit_days)
        med_limit = today + datetime.timedelta(days=med_days)

        status_norm = (status or '').strip().capitalize()
        if status_norm == 'Expired':
            return self.filter(expiry_date__lt=today)
        elif status_norm == 'Critical':
            return self.filter(expiry_date__gte=today, expiry_date__lte=crit_limit)
        elif status_norm == 'Medium':
            return self.filter(expiry_date__gt=crit_limit, expiry_date__lte=med_limit)
        elif status_norm == 'Low':
            return self.filter(expiry_date__gt=med_limit)
        return self

    def active_surplus(self):
        """Returns items that are not expired, suitable for donation/rescue."""
        today = timezone.localdate()
        return self.filter(expiry_date__gte=today)


class FoodItemManager(models.Manager):
    def get_queryset(self):
        return FoodItemQuerySet(self.model, using=self._db)

    def filter_by_status(self, status):
        return self.get_queryset().filter_by_status(status)

    def active_surplus(self):
        return self.get_queryset().active_surplus()


class FoodItem(models.Model):
    CATEGORY_CHOICES = [
        ('Produce', 'Fresh Produce (Fruits & Vegetables)'),
        ('Dairy', 'Dairy & Eggs'),
        ('Bakery', 'Bakery & Bread'),
        ('Meat', 'Meat & Poultry'),
        ('Seafood', 'Fish & Seafood'),
        ('Pantry', 'Pantry & Canned Goods'),
        ('Prepared Meals', 'Prepared Meals & Deli'),
        ('Beverages', 'Beverages'),
        ('Other', 'Other'),
    ]

    UNIT_CHOICES = [
        ('kg', 'Kilograms (kg)'),
        ('g', 'Grams (g)'),
        ('lbs', 'Pounds (lbs)'),
        ('units', 'Units / Items'),
        ('packs', 'Packs / Cartons'),
        ('litres', 'Litres (L)'),
        ('boxes', 'Boxes'),
        ('cans', 'Cans'),
        ('portions', 'Portions / Servings'),
    ]

    name = models.CharField(max_length=200, verbose_name="Food Name")
    category = models.CharField(
        max_length=50,
        choices=CATEGORY_CHOICES,
        default='Other',
        verbose_name="Category"
    )
    quantity = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        verbose_name="Quantity",
        help_text="Quantity must be greater than 0."
    )
    unit = models.CharField(
        max_length=20,
        choices=UNIT_CHOICES,
        default='units',
        verbose_name="Unit of Measurement"
    )
    description = models.TextField(
        blank=True,
        default="",
        verbose_name="Food Description",
        help_text="Optional details such as storage instructions, packaging state, etc."
    )
    expiry_date = models.DateField(
        verbose_name="Expiry Date",
        help_text="Date when this food item expires."
    )
    batch_number = models.CharField(
        max_length=100,
        blank=True,
        default="",
        verbose_name="Batch Number",
        help_text="Optional batch or lot number for inventory tracking."
    )
    storage_location = models.CharField(
        max_length=150,
        blank=True,
        default="",
        verbose_name="Storage Location",
        help_text="Optional shelf, cold room, or section identifier."
    )
    date_added = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Date Created"
    )
    date_updated = models.DateTimeField(
        auto_now=True,
        verbose_name="Date Updated"
    )
    donor_info = models.CharField(
        max_length=255,
        blank=True,
        default="",
        verbose_name="Donor / Business Information",
        help_text="Donor, supermarket, restaurant, or individual provider."
    )
    added_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="food_items",
        verbose_name="Added By (Owner)"
    )

    objects = FoodItemManager()

    class Meta:
        ordering = ['expiry_date', 'name']
        verbose_name = "Food Item"
        verbose_name_plural = "Food Items"

    def __str__(self):
        return f"{self.name} ({self.quantity} {self.unit}) - Exp: {self.expiry_date}"

    def clean(self):
        super().clean()
        if self.quantity is not None and self.quantity <= 0:
            raise ValidationError({'quantity': 'Quantity must be strictly greater than 0.'})

    @property
    def days_until_expiry(self):
        """Calculates days remaining until expiry relative to current local date."""
        today = timezone.localdate()
        return (self.expiry_date - today).days

    @property
    def expiry_status(self):
        """
        Dynamically calculates expiry status:
        - EXPIRED: Expiry date has passed (< 0 days)
        - CRITICAL: Expires today or within 2 days (0 <= days <= 2)
        - MEDIUM: Expires in 3 to 7 days (3 <= days <= 7)
        - LOW: Expires in more than 7 days (> 7 days)
        Thresholds are configurable in settings.EXPIRY_THRESHOLDS.
        """
        thresholds = get_expiry_thresholds()
        crit_days = thresholds.get('CRITICAL_DAYS', 2)
        med_days = thresholds.get('MEDIUM_DAYS', 7)

        days = self.days_until_expiry
        if days < 0:
            return 'Expired'
        elif days <= crit_days:
            return 'Critical'
        elif days <= med_days:
            return 'Medium'
        else:
            return 'Low'

    @property
    def expiry_badge_class(self):
        """Returns Bootstrap badge color class for UI representation."""
        status = self.expiry_status
        if status == 'Expired':
            return 'danger'
        elif status == 'Critical':
            return 'danger'
        elif status == 'Medium':
            return 'warning'
        else:
            return 'success'

    @property
    def waste_risk_score(self):
        """
        Transparent rule-based AI Waste Risk Score (0 - 100).
        Calculates loss probability using shelf-life remaining and category perishability:
        - Expired: 100 (Immediate Loss)
        - 0 days (today): 95
        - 1 day: 90
        - 2 days: 85
        - 3-7 days: 50 - 70
        - > 7 days: 10 - 30
        Highly perishable categories (Dairy, Meat, Seafood, Produce) carry a +5 risk weighting.
        """
        days = self.days_until_expiry
        if days < 0:
            return 100
        elif days == 0:
            base_score = 95
        elif days == 1:
            base_score = 90
        elif days == 2:
            base_score = 85
        elif days <= 4:
            base_score = 70
        elif days <= 7:
            base_score = 50
        elif days <= 14:
            base_score = 30
        else:
            base_score = 15

        # Category perishability adjustment
        perishable_categories = ['Dairy', 'Meat', 'Seafood', 'Produce', 'Prepared Meals']
        if self.category in perishable_categories and days >= 0:
            base_score = min(base_score + 5, 95)

        return base_score

    @property
    def waste_risk_level(self):
        """Semantic risk level for display."""
        score = self.waste_risk_score
        if score >= 85:
            return 'High Risk'
        elif score >= 50:
            return 'Moderate Risk'
        else:
            return 'Low Risk'

    @property
    def waste_risk_badge_class(self):
        score = self.waste_risk_score
        if score >= 85:
            return 'danger'
        elif score >= 50:
            return 'warning'
        else:
            return 'success'
