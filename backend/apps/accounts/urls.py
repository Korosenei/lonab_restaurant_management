"""
URLs complètes pour accounts app
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from .urls_placeholder import urlpatterns as placeholder_urls

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
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('password-reset/', views.password_reset_view, name='password_reset'),

    # ============================================
    # DASHBOARD REDIRECTS
    # ============================================
    path('dashboard/', views.dashboard_redirection, name='dashboard'),
    path('dashboard/client/', views.dashboard_client, name='client_dashboard'),
    path('dashboard/caissier/', views.dashboard_caissier, name='caissier_dashboard'),
    path('dashboard/restaurant/', views.dashboard_restaurant, name='restaurant_dashboard'),
    path('dashboard/admin/', views.dashboard_admin, name='admin_dashboard'),

    # ============================================
    # USER MANAGEMENT
    # ============================================
    path('users/', views.users_list, name='users_list'),
    path('users/create/', views.user_create, name='user_create'),
    path('users/<int:pk>/', views.user_detail, name='user_detail'),
    path('users/<int:pk>/edit/', views.user_edit, name='user_edit'),
    path('users/<int:pk>/delete/', views.user_delete, name='user_delete'),

    # ============================================
    # PROFILE MANAGEMENT
    # ============================================
    path('profile/', views.profile_view, name='profile'),
    path('profile/update/', views.profile_update, name='profile_update'),
    path('profile/change-password/', views.change_password, name='change_password'),

    # ============================================
    # DIRECTION MANAGEMENT
    # ============================================
    path('directions/', views.directions_list, name='directions_list'),
    path('directions/create/', views.direction_create, name='direction_create'),
    path('directions/<int:pk>/', views.direction_detail, name='direction_detail'),
    path('directions/<int:pk>/edit/', views.direction_edit, name='direction_edit'),
    path('directions/<int:pk>/delete/', views.direction_delete, name='direction_delete'),

    # ============================================
    # AGENCY MANAGEMENT
    # ============================================
    path('agences/', views.agences_list, name='agences_list'),
    path('agences/create/', views.agence_create, name='agence_create'),
    path('agences/<int:pk>/', views.agence_detail, name='agence_detail'),
    path('agences/<int:pk>/edit/', views.agence_edit, name='agence_edit'),
    path('agences/<int:pk>/delete/', views.agence_delete, name='agence_delete'),

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

# Add placeholder URLs for pages not yet implemented
urlpatterns += placeholder_urls