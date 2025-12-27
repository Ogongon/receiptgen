from django.urls import path
from . import views

urlpatterns = [
    # Public Pages
    path('', views.landing_page, name='home'),
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),

    # Protected App
    path('dashboard/', views.dashboard, name='dashboard'),
    path('settings/', views.update_settings, name='update_settings'),
    path('download/<int:receipt_id>/', views.download_pdf, name='download_pdf'),
    path('clear/', views.clear_dashboard, name='clear_dashboard'),
]