import os
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login as auth_login, logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.http import HttpResponse, Http404
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone

from .models import FoodItem, UserProfile
from .forms import (
    UserRegisterForm,
    UserLoginForm,
    FoodItemForm,
    CSVUploadForm,
)
from .csv_utils import process_csv_file


def register_view(request):
    """
    User registration supporting Business and NGO roles.
    Strictly forbids public creation of administrator/staff accounts.
    """
    if request.user.is_authenticated:
        return redirect_user_to_dashboard(request.user)

    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            auth_login(request, user)
            role_display = user.profile.get_role_display()
            messages.success(
                request,
                f"Welcome, {user.username}! Your {role_display} account has been registered successfully."
            )
            return redirect_user_to_dashboard(user)
        else:
            messages.error(request, "Registration could not be completed. Please correct the highlighted errors.")
    else:
        form = UserRegisterForm()

    return render(request, 'inventory/register.html', {'form': form})


def login_view(request):
    """Secure user login with role-aware redirection."""
    if request.user.is_authenticated:
        return redirect_user_to_dashboard(request.user)

    if request.method == 'POST':
        form = UserLoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            auth_login(request, user)
            messages.success(request, f"Welcome back, {user.username}!")
            next_url = request.GET.get('next')
            if next_url:
                return redirect(next_url)
            return redirect_user_to_dashboard(user)
        else:
            messages.error(request, "Invalid username or password. Please try again.")
    else:
        form = UserLoginForm()

    return render(request, 'inventory/login.html', {'form': form})


def logout_view(request):
    """User logout view."""
    auth_logout(request)
    messages.info(request, "You have been safely logged out.")
    return redirect('login')


def redirect_user_to_dashboard(user):
    """Route user according to their role (Business -> inventory, NGO -> ngo_dashboard)."""
    if hasattr(user, 'profile') and user.profile.is_ngo:
        return redirect('ngo_dashboard')
    return redirect('inventory_list')


@login_required
def inventory_list(request):
    """
    Business Inventory Dashboard with strict ownership isolation.
    Businesses only view and manage their own inventory items.
    Administrators/staff can view all inventory.
    """
    # Role check: if NGO, redirect to their dedicated surplus view
    if hasattr(request.user, 'profile') and request.user.profile.is_ngo and not request.user.is_staff:
        return redirect('ngo_dashboard')

    # Ownership isolation: businesses see only their own items
    if request.user.is_staff:
        base_qs = FoodItem.objects.all()
    else:
        base_qs = FoodItem.objects.filter(added_by=request.user)

    items = base_qs

    # Query parameters
    search_query = request.GET.get('q', '').strip()
    category_filter = request.GET.get('category', '').strip()
    status_filter = request.GET.get('status', '').strip()
    expiry_before = request.GET.get('expiry_before', '').strip()
    sort_by = request.GET.get('sort_by', 'expiry_date').strip()

    # Search by food name, description, donor, batch number
    if search_query:
        items = items.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(donor_info__icontains=search_query) |
            Q(batch_number__icontains=search_query)
        )

    # Filter by category
    if category_filter:
        items = items.filter(category=category_filter)

    # Filter by expiry date threshold
    if expiry_before:
        try:
            items = items.filter(expiry_date__lte=expiry_before)
        except Exception:
            pass

    # Filter by dynamic expiry status
    if status_filter:
        items = items.filter_by_status(status_filter)

    # Sorting
    valid_sort_fields = [
        'expiry_date', '-expiry_date', 'name', '-name',
        'quantity', '-quantity', '-date_added'
    ]
    if sort_by in valid_sort_fields:
        items = items.order_by(sort_by)
    else:
        items = items.order_by('expiry_date')

    # Dashboard counters strictly based on authorized queryset
    total_count = base_qs.count()
    expired_count = base_qs.filter_by_status('Expired').count()
    critical_count = base_qs.filter_by_status('Critical').count()
    medium_count = base_qs.filter_by_status('Medium').count()
    low_count = base_qs.filter_by_status('Low').count()

    # High-priority alerts for critical or expired inventory
    critical_items = base_qs.filter_by_status('Critical')[:5]
    expired_items = base_qs.filter_by_status('Expired')[:5]

    context = {
        'items': items,
        'search_query': search_query,
        'category_filter': category_filter,
        'status_filter': status_filter,
        'expiry_before': expiry_before,
        'sort_by': sort_by,
        'categories': FoodItem.CATEGORY_CHOICES,
        'total_count': total_count,
        'expired_count': expired_count,
        'critical_count': critical_count,
        'medium_count': medium_count,
        'low_count': low_count,
        'critical_items': critical_items,
        'expired_items': expired_items,
        'today': timezone.localdate(),
        'is_admin': request.user.is_staff,
    }
    return render(request, 'inventory/inventory_list.html', context)


@login_required
def ngo_dashboard(request):
    """
    Dedicated NGO / Community Kitchen Dashboard.
    Displays all available active surplus food across providers ready for rescue/redistribution.
    """
    # Active surplus items (unexpired, ready for donation)
    base_qs = FoodItem.objects.active_surplus()
    items = base_qs

    # Filters
    search_query = request.GET.get('q', '').strip()
    category_filter = request.GET.get('category', '').strip()
    status_filter = request.GET.get('status', '').strip()
    sort_by = request.GET.get('sort_by', 'expiry_date').strip()

    if search_query:
        items = items.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(donor_info__icontains=search_query)
        )

    if category_filter:
        items = items.filter(category=category_filter)

    if status_filter:
        items = items.filter_by_status(status_filter)

    valid_sort_fields = ['expiry_date', '-expiry_date', 'name', '-name', 'quantity', '-quantity']
    if sort_by in valid_sort_fields:
        items = items.order_by(sort_by)
    else:
        items = items.order_by('expiry_date')

    total_surplus = base_qs.count()
    critical_surplus = base_qs.filter_by_status('Critical').count()
    medium_surplus = base_qs.filter_by_status('Medium').count()
    low_surplus = base_qs.filter_by_status('Low').count()

    context = {
        'items': items,
        'search_query': search_query,
        'category_filter': category_filter,
        'status_filter': status_filter,
        'sort_by': sort_by,
        'categories': FoodItem.CATEGORY_CHOICES,
        'total_surplus': total_surplus,
        'critical_surplus': critical_surplus,
        'medium_surplus': medium_surplus,
        'low_surplus': low_surplus,
        'today': timezone.localdate(),
    }
    return render(request, 'inventory/ngo_dashboard.html', context)


@login_required
def food_detail(request, pk):
    """View details of an individual food item with role-based actions."""
    item = get_object_or_404(FoodItem, pk=pk)

    # Authorization: item can be viewed if user is staff, owner, or if user is NGO viewing active surplus
    is_owner = (item.added_by == request.user)
    is_staff = request.user.is_staff
    is_ngo = hasattr(request.user, 'profile') and request.user.profile.is_ngo

    if not (is_owner or is_staff or is_ngo):
        raise PermissionDenied("You do not have permission to view this item.")

    return render(request, 'inventory/food_detail.html', {
        'item': item,
        'can_edit': is_owner or is_staff,
    })


@login_required
def food_create(request):
    """Create a new food inventory item. Reserved for Food Providers and Admins."""
    if hasattr(request.user, 'profile') and request.user.profile.is_ngo and not request.user.is_staff:
        messages.warning(request, "NGO accounts cannot create inventory items; you can view available surplus on the NGO dashboard.")
        return redirect('ngo_dashboard')

    if request.method == 'POST':
        form = FoodItemForm(request.POST)
        if form.is_valid():
            item = form.save(commit=False)
            item.added_by = request.user
            # Default donor_info to organization name if omitted
            if not item.donor_info and hasattr(request.user, 'profile') and request.user.profile.organization_name:
                item.donor_info = request.user.profile.organization_name
            item.save()
            messages.success(request, f"Food item '{item.name}' added to inventory successfully!")
            return redirect('food_detail', pk=item.pk)
        else:
            messages.error(request, "Please check the form for errors.")
    else:
        # Prepopulate donor_info with business organization name
        initial = {}
        if hasattr(request.user, 'profile') and request.user.profile.organization_name:
            initial['donor_info'] = request.user.profile.organization_name
        form = FoodItemForm(initial=initial)

    return render(request, 'inventory/food_form.html', {
        'form': form,
        'title': 'Add New Food Item',
        'button_text': 'Add Item',
    })


@login_required
def food_update(request, pk):
    """Update an existing food item. Enforces strict ownership check."""
    item = get_object_or_404(FoodItem, pk=pk)

    # Ownership enforcement
    if item.added_by != request.user and not request.user.is_staff:
        raise PermissionDenied("You do not have permission to edit this item.")

    if request.method == 'POST':
        form = FoodItemForm(request.POST, instance=item)
        if form.is_valid():
            form.save()
            messages.success(request, f"Food item '{item.name}' updated successfully!")
            return redirect('food_detail', pk=item.pk)
        else:
            messages.error(request, "Please check the form for errors.")
    else:
        form = FoodItemForm(instance=item)

    return render(request, 'inventory/food_form.html', {
        'form': form,
        'title': f"Edit: {item.name}",
        'button_text': 'Save Changes',
        'item': item,
    })


@login_required
def food_delete(request, pk):
    """Delete a food item with confirmation. Enforces strict ownership check."""
    item = get_object_or_404(FoodItem, pk=pk)

    # Ownership enforcement
    if item.added_by != request.user and not request.user.is_staff:
        raise PermissionDenied("You do not have permission to delete this item.")

    if request.method == 'POST':
        item_name = item.name
        item.delete()
        messages.success(request, f"Food item '{item_name}' was removed from inventory.")
        return redirect('inventory_list')

    return render(request, 'inventory/food_confirm_delete.html', {'item': item})


@login_required
def csv_upload_view(request):
    """Batch import food records from CSV with owner attribution and validation."""
    if hasattr(request.user, 'profile') and request.user.profile.is_ngo and not request.user.is_staff:
        messages.warning(request, "NGO accounts cannot upload inventory; view available surplus on the NGO dashboard.")
        return redirect('ngo_dashboard')

    result = None
    if request.method == 'POST':
        form = CSVUploadForm(request.POST, request.FILES)
        if form.is_valid():
            uploaded_file = request.FILES['csv_file']
            result = process_csv_file(uploaded_file, user=request.user)
            if result['success_count'] > 0:
                messages.success(
                    request,
                    f"Successfully imported {result['success_count']} food item(s)."
                )
            if result['failed_count'] > 0:
                messages.warning(
                    request,
                    f"{result['failed_count']} row(s) could not be imported due to validation errors."
                )
        else:
            messages.error(request, "Please select a valid CSV file.")
    else:
        form = CSVUploadForm()

    return render(request, 'inventory/csv_upload.html', {
        'form': form,
        'result': result,
    })


@login_required
def download_sample_csv(request):
    """Provide downloadable sample CSV file."""
    sample_path = os.path.join(settings.BASE_DIR, 'sample_food_inventory.csv')
    if not os.path.exists(sample_path):
        raise Http404("Sample CSV file not found.")

    with open(sample_path, 'r', encoding='utf-8') as f:
        response = HttpResponse(f.read(), content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="sample_food_inventory.csv"'
        return response
