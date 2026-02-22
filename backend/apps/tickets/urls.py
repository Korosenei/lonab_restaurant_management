"""
URLs pour l'application tickets
"""
from django.urls import path
from . import views

app_name = 'tickets'

urlpatterns = [
    # ── Admin ──────────────────────────────────────────────────
    path('', views.admin_tickets_list, name='admin_tickets'),
    path('stats/', views.admin_tickets_stats, name='admin_stats'),
    path('<int:pk>/', views.ticket_detail, name='ticket_detail'),

    # ── Caissier ───────────────────────────────────────────────
    path('caissier/', views.caissier_tickets, name='caissier_tickets'),

    # ── Client ─────────────────────────────────────────────────
    path('client/', views.client_tickets, name='client_tickets'),
    path('client/qrcode/', views.client_qrcode, name='client_qrcode'),
    path('client/qrcode/generer/', views.generer_qrcode, name='generer_qrcode'),
    path('client/qrcode/<int:pk>/invalider/', views.invalider_qrcode, name='invalider_qrcode'),
]