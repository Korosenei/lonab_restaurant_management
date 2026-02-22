from django.urls import path
from . import views

app_name = 'restaurants'

urlpatterns = [
    # Admin + Caissier : Restaurants
    path('', views.restaurants_list, name='restaurants_list'),
    path('create/', views.restaurant_create, name='restaurant_create'),
    path('<int:pk>/edit/', views.restaurant_edit, name='restaurant_edit'),
    path('<int:pk>/delete/', views.restaurant_delete, name='restaurant_delete'),
    path('<int:pk>/', views.restaurant_detail, name='restaurant_detail'),

    # Menus
    path('menus/', views.menus_list, name='menus_list'),
    path('menus/create/', views.menu_create, name='menu_create'),
    path('menus/<int:pk>/edit/', views.menu_edit, name='menu_edit'),
    path('menus/<int:pk>/delete/', views.menu_delete, name='menu_delete'),

    # Plannings
    path('plannings/', views.plannings_list, name='plannings_list'),
    path('plannings/create/', views.planning_create, name='planning_create'),
    path('plannings/<int:pk>/edit/', views.planning_edit, name='planning_edit'),
    path('plannings/<int:pk>/delete/', views.planning_delete, name='planning_delete'),

    # Gestionnaire
    path('gestionnaire/', views.gestionnaire_dashboard, name='gestionnaire_dashboard'),
    path('gestionnaire/scanner/', views.gestionnaire_scanner, name='gestionnaire_scanner'),
    path('gestionnaire/scanner/verifier/', views.verifier_qr_code, name='verifier_qr_code'),
    path('gestionnaire/scanner/valider/', views.valider_qr_code, name='valider_qr_code'),
    path('gestionnaire/consommations/', views.gestionnaire_consommations, name='gestionnaire_consommations'),
    path('gestionnaire/reservations/', views.gestionnaire_reservations, name='gestionnaire_reservations'),
    path('gestionnaire/reservations/<int:pk>/statut/', views.gestionnaire_changer_statut_reservation, name='changer_statut_reservation'),
    path('gestionnaire/agences/', views.gestionnaire_agences, name='gestionnaire_agences'),

    # Client
    path('client/restaurants/', views.client_restaurants, name='client_restaurants'),
    path('client/menus/', views.client_menus, name='client_menus'),
    path('client/reservations/', views.client_reservations, name='client_reservations'),
    path('client/reserver/', views.client_reserver, name='client_reserver'),
    path('client/reservations/<int:pk>/annuler/', views.client_annuler_reservation, name='client_annuler'),

    # Caissier
    path('caissier/planifier/', views.caissier_planifier_restaurant, name='caissier_planifier'),
]