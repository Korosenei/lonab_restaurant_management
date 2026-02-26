"""
URLs pour l'application transactions
"""
from django.urls import path
from . import views

app_name = 'transactions'

urlpatterns = [
    # ── Admin ──────────────────────────────────────────────────
    path('', views.admin_transactions, name='admin_transactions'),
    path('<int:pk>/', views.transaction_detail, name='transaction_detail'),
    path('stats/', views.admin_stats, name='transaction_stats'),

    # ── Caissier ───────────────────────────────────────────────
    path('caissier/vente/', views.caissier_confirmer_vente, name='caissier_confirmer_vente'),
    path('caissier/historique/', views.caissier_historique, name='caissier_historique'),
    path('caissier/clients/', views.caissier_clients, name='caissier_clients'),
    path('caissier/clients/<int:pk>/', views.caissier_client_detail, name='caissier_client_detail'),
    path('caissier/transaction/<int:pk>/rembourser/', views.rembourser_transaction, name='rembourser'),

    # ── Client ─────────────────────────────────────────────────
    path('client/', views.client_historique, name='client_historique'),
]