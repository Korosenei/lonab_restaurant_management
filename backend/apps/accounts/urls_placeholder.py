"""
Temporary URL placeholders for undefined views
This file provides placeholder URLs to avoid NoReverseMatch errors
"""
from django.urls import path
from django.http import HttpResponse
from django.shortcuts import render

def placeholder_view(request):
    """Placeholder view for URLs not yet implemented"""
    return HttpResponse("""
        <html>
        <head><title>En construction</title></head>
        <body style="font-family: Arial; text-align: center; padding: 50px;">
            <h1>🚧 Page en construction</h1>
            <p>Cette fonctionnalité sera disponible prochainement.</p>
            <a href="javascript:history.back()" style="color: #28a745;">← Retour</a>
        </body>
        </html>
    """)

# Placeholders pour les URLs manquantes
urlpatterns = [
    # Client URLs
    path('client/tickets/', placeholder_view, name='client_tickets'),
    path('client/qrcode/', placeholder_view, name='client_qrcode'),

    # Caissier URLs
    path('caissier/reports/', placeholder_view, name='caissier_reports'),

    # Restaurant Manager URLs
    path('restaurant/scan/', placeholder_view, name='restaurant_scan'),
    path('restaurant/consumptions/', placeholder_view, name='restaurant_consumptions'),
    path('restaurant/menus/', placeholder_view, name='restaurant_menus'),
    path('restaurant/reservations/', placeholder_view, name='restaurant_reservations'),
    path('restaurant/agencies/', placeholder_view, name='restaurant_agencies'),
    path('restaurant/stats/', placeholder_view, name='restaurant_stats'),
    path('restaurant/history/', placeholder_view, name='restaurant_history'),

    # Admin URLs
    path('admin/overview/', placeholder_view, name='admin_overview'),
    path('admin/reports/', placeholder_view, name='admin_reports'),
    path('admin/audit/', placeholder_view, name='admin_audit'),
    path('admin/settings/', placeholder_view, name='admin_settings'),
    path('admin/notifications/', placeholder_view, name='admin_notifications'),

    # Generic URLs
    path('notifications/', placeholder_view, name='notifications_list'),
    path('profile/', placeholder_view, name='profile'),
    path('settings/', placeholder_view, name='settings'),
]