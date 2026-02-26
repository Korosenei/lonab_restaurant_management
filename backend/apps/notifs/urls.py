from django.urls import path
from . import views

app_name = 'notifs'

urlpatterns = [
    # Admin
    path('admin/', views.admin_notifications, name='admin_notifications'),
    path('envoyer/', views.envoyer, name='envoyer'),
    path('tout-marquer-lu/', views.marquer_tout_lu, name='marquer_tout_lu'),
    path('<int:pk>/marquer-lu/', views.marquer_lu, name='marquer_lu'),
    path('<int:pk>/supprimer/', views.supprimer, name='supprimer'),

    # Client
    path('mes-notifications/', views.mes_notifications, name='mes_notifications'),

    # API
    path('api/', views.api_notifs, name='api_notifs'),
]
