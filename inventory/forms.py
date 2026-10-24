from decimal import Decimal
from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from .models import FoodItem, UserProfile


class UserRegisterForm(UserCreationForm):
    """
    Registration form supporting both Business / Food Providers and NGOs / Community Kitchens.
    Strictly forbids public creation of admin or staff accounts.
    """
    ROLE_CHOICES = [
        ('business', 'Business / Food Provider (Restaurant, Supermarket, Bakery, etc.)'),
        ('ngo', 'NGO / Community Kitchen (Food Rescue & Charity Recipient)'),
    ]

    role = forms.ChoiceField(
        choices=ROLE_CHOICES,
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'}),
        initial='business',
        label="Account Type"
    )
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'name@organization.org'}),
        label="Email Address"
    )
    organization_name = forms.CharField(
        required=True,
        max_length=255,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Green Valley Grocery or Hope Kitchen'}),
        label="Organization / Business Name"
    )
    contact_person = forms.CharField(
        required=False,
        max_length=150,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Full name of primary coordinator'}),
        label="Contact Person"
    )
    phone = forms.CharField(
        required=False,
        max_length=50,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., +1 555-0199'}),
        label="Phone Number"
    )
    address = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Physical address or pickup/delivery area'}),
        label="Address / Location"
    )

    class Meta:
        model = User
        fields = ['username', 'email']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Choose a unique username'
        })
        self.fields['username'].help_text = "Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only."
        # Style password fields from UserCreationForm
        if 'password1' in self.fields:
            self.fields['password1'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Create strong password'})
        if 'password2' in self.fields:
            self.fields['password2'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Confirm your password'})

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip().lower()
        if not email:
            raise ValidationError("Email address is required.")
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError("An account with this email address already exists.")
        return email

    def clean_role(self):
        role = self.cleaned_data.get('role')
        if role not in ['business', 'ngo']:
            raise ValidationError("Please select a valid account role.")
        return role

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.is_staff = False
        user.is_superuser = False
        if commit:
            user.save()
            profile, _ = UserProfile.objects.get_or_create(user=user)
            profile.role = self.cleaned_data['role']
            profile.organization_name = self.cleaned_data.get('organization_name', '')
            profile.contact_person = self.cleaned_data.get('contact_person', '')
            profile.phone = self.cleaned_data.get('phone', '')
            profile.address = self.cleaned_data.get('address', '')
            profile.save()
        return user


class UserLoginForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Enter your username',
            'autofocus': True,
        })
        self.fields['password'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Enter your password',
        })


class FoodItemForm(forms.ModelForm):
    class Meta:
        model = FoodItem
        fields = [
            'name',
            'category',
            'quantity',
            'unit',
            'expiry_date',
            'batch_number',
            'storage_location',
            'donor_info',
            'description',
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., Organic Whole Milk, Whole Grain Bread, Gala Apples',
            }),
            'category': forms.Select(attrs={
                'class': 'form-select',
            }),
            'quantity': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0.01',
                'placeholder': 'e.g., 10.00',
            }),
            'unit': forms.Select(attrs={
                'class': 'form-select',
            }),
            'expiry_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
            }),
            'batch_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Optional lot or batch tracking code (e.g., LOT-2026-A1)',
            }),
            'storage_location': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Optional storage area (e.g., Walk-in Chiller 2, Shelf B)',
            }),
            'donor_info': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Donor / Provider or branch name',
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Storage instructions, packaging status, allergens, or handling notes...',
            }),
        }

    def clean_name(self):
        name = self.cleaned_data.get('name', '').strip()
        if not name:
            raise ValidationError("Food name cannot be empty.")
        return name

    def clean_quantity(self):
        qty = self.cleaned_data.get('quantity')
        if qty is None or qty <= Decimal('0'):
            raise ValidationError("Quantity must be greater than zero.")
        return qty


class CSVUploadForm(forms.Form):
    csv_file = forms.FileField(
        label="Select Inventory CSV File",
        widget=forms.FileInput(attrs={'class': 'form-control', 'accept': '.csv'}),
        help_text="Upload a .csv file formatted with headers: food_name, category, quantity, unit, expiry_date."
    )

    def clean_csv_file(self):
        file = self.cleaned_data.get('csv_file')
        if not file:
            raise ValidationError("No file was uploaded.")

        if not file.name.lower().endswith('.csv'):
            raise ValidationError("Uploaded file must have a .csv extension.")

        # Limit file size to 5MB to prevent memory exhaustion
        if file.size > 5 * 1024 * 1024:
            raise ValidationError("CSV file size must not exceed 5MB.")

        return file
