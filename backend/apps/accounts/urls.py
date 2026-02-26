"""
URLs complètes pour accounts app
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from . import exports
from .dashboard_views import (
    dashboard_redirection,
    admin_dashboard,
    caissier_dashboard,
    gestionnaire_dashboard,
    client_dashboard,
)

app_name = 'accounts'

# API Router
router = DefaultRouter()
router.register(r'users', views.UtilisateurViewSet, basename='user')
router.register(r'directions', views.DirectionViewSet, basename='direction')
router.register(r'agencies', views.AgenceViewSet, basename='agency')
router.register(r'profiles', views.ProfilUtilisateurViewSet, basename='profile')

# URL Patterns
urlpatterns = [
    # ============================================
    # AUTHENTICATION (Template views)
    # ============================================
    path('', views.login_view, name='login'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('password-reset/', views.password_reset_view, name='password_reset'),

    # ============================================
    # DASHBOARD REDIRECTS
    # ============================================
    path('dashboard/', dashboard_redirection, name='dashboard'),
    path('dashboard/admin/', admin_dashboard, name='admin_dashboard'),
    path('dashboard/caissier/', caissier_dashboard, name='caissier_dashboard'),
    path('dashboard/gestionnaire/', gestionnaire_dashboard, name='gestionnaire_dashboard'),
    path('dashboard/client/', client_dashboard, name='client_dashboard'),

    # ============================================
    # USER MANAGEMENT
    # ============================================
    path('dashboard/admin/users/', views.users_list, name='users_list'),
    path('dashboard/admin/users/create/', views.user_create, name='user_create'),
    path('dashboard/admin/users/<int:pk>/', views.user_detail, name='user_detail'),
    path('dashboard/admin/users/<int:pk>/edit/', views.user_edit, name='user_edit'),
    path('dashboard/admin/users/<int:pk>/delete/', views.user_delete, name='user_delete'),

    # ============================================
    # PROFILE MANAGEMENT
    # ============================================
    path('profile/', views.profile_view, name='profile'),
    path('profile/update/', views.profile_update, name='profile_update'),
    path('profile/change-password/', views.change_password, name='change_password'),

    # ============================================
    # DIRECTION MANAGEMENT
    # ============================================
    path('dashboard/admin/directions/', views.directions_list, name='directions_list'),
    path('dashboard/admin/directions/create/', views.direction_create, name='direction_create'),
    path('dashboard/admin/directions/<int:pk>/', views.direction_detail, name='direction_detail'),
    path('dashboard/admin/directions/<int:pk>/edit/', views.direction_edit, name='direction_edit'),
    path('dashboard/admin/directions/<int:pk>/delete/', views.direction_delete, name='direction_delete'),

    # ============================================
    # AGENCY MANAGEMENT
    # ============================================
    path('dashboard/admin/agences/', views.agences_list, name='agences_list'),
    path('dashboard/admin/agences/create/', views.agence_create, name='agence_create'),
    path('dashboard/admin/agences/<int:pk>/', views.agence_detail, name='agence_detail'),
    path('dashboard/admin/agences/<int:pk>/edit/', views.agence_edit, name='agence_edit'),
    path('dashboard/admin/agences/<int:pk>/delete/', views.agence_delete, name='agence_delete'),

    # ── Exports Utilisateurs ──
    path('exports/users/pdf/', exports.export_users_pdf, name='export_users_pdf'),
    path('exports/users/excel/', exports.export_users_excel, name='export_users_excel'),

    # ── Exports Directions ──
    path('exports/directions/pdf/', exports.export_directions_pdf, name='export_directions_pdf'),
    path('exports/directions/excel/', exports.export_directions_excel, name='export_directions_excel'),

    # ── Exports Agences ──
    path('exports/agences/pdf/', exports.export_agencies_pdf, name='export_agencies_pdf'),
    path('exports/agences/excel/', exports.export_agencies_excel, name='export_agencies_excel'),

    # ============================================
    # EXPORTS
    # ============================================
    path('export/users/pdf/', views.export_users_pdf, name='export_users_pdf'),
    path('export/users/excel/', views.export_users_excel, name='export_users_excel'),
    path('export/directions/pdf/', views.export_directions_pdf, name='export_directions_pdf'),
    path('export/agencies/excel/', views.export_agencies_excel, name='export_agencies_excel'),

    # ============================================
    # API ENDPOINTS
    # ============================================
    path('api/', include(router.urls)),
    path('api/login/', views.api_connexion, name='api_login'),
    path('api/logout/', views.api_deconnexion, name='api_logout'),
    path('api/profile/update/', views.api_mise_a_jour_profil, name='api_profile_update'),
]
