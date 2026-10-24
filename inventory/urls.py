from django.urls import path
from . import views

urlpatterns = [
    # Inventory CRUD
    path('', views.inventory_list, name='inventory_list'),
    path('item/<int:pk>/', views.food_detail, name='food_detail'),
    path('item/add/', views.food_create, name='food_create'),
    path('item/<int:pk>/edit/', views.food_update, name='food_update'),
    path('item/<int:pk>/delete/', views.food_delete, name='food_delete'),

    # CSV Import & Sample Download
    path('csv/upload/', views.csv_upload_view, name='csv_upload'),
    path('csv/sample/', views.download_sample_csv, name='download_sample_csv'),

    # NGO Community Kitchen Portal
    path('ngo/dashboard/', views.ngo_dashboard, name='ngo_dashboard'),

    # Authentication
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
]
