"""
URL configuration for LONAB Restaurant Management project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
)

urlpatterns = [
    path('admin/', admin.site.urls),

    # Authentication et Dashboard
    path('', include('apps.accounts.urls')),
    path('accounts/', include('apps.accounts.urls')),
    path('restaurants/', include('apps.restaurants.urls')),
    path('transactions/', include('apps.transactions.urls')),
    path('tickets/', include('apps.tickets.urls')),
    path('settings/', include('apps.settings.urls')),
    path('notifications/', include('apps.notifs.urls')),

    # API Authentication
    path('api/auth/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/auth/token/verify/', TokenVerifyView.as_view(), name='token_verify'),

    # API Endpoints
    # path('api/accounts/', include('apps.accounts.urls')),
    # path('api/tickets/', include('apps.tickets.urls')),
    # path('api/restaurants/', include('apps.restaurants.urls')),
    # path('api/transactions/', include('apps.transactions.urls')),
    # path('api/notifications/', include('apps.notifications.urls')),
    # path('api/settings/', include('apps.settings.urls')),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# Admin customization
admin.site.site_header = f"{settings.COMPANY_NAME} - {settings.MUTUELLE_NAME}"
admin.site.site_title = "Gestion des Tickets"
admin.site.index_title = "Administration"
