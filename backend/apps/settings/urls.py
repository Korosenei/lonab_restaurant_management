from django.urls import path
from . import views

app_name = 'settings'

urlpatterns = [
    path('', views.admin_settings, name='admin_settings'),
    path('audit/', views.admin_audit, name='admin_audit'),
    path('jours-feries/create/', views.jour_ferie_create, name='jour_ferie_create'),
    path('jours-feries/<int:pk>/delete/', views.jour_ferie_delete, name='jour_ferie_delete'),

    path('admin/overview/', views.admin_overview, name='admin_overview'),
    path('admin/reports/', views.admin_reports, name='admin_reports'),

    path('api/params/', views.api_params, name='api_params'),
]
