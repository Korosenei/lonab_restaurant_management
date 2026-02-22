"""
Configuration de l'administration pour l'application restaurants
"""
from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from .models import Restaurant, PlanningRestaurant, Menu, Reservation


@admin.register(Restaurant)
class RestaurantAdmin(admin.ModelAdmin):
    list_display = ['logo_display', 'nom', 'code', 'ville', 'telephone',
                    'en_service_actuel', 'statut_display', 'nb_menus', 'date_creation']
    list_display_links = ['logo_display', 'nom']
    list_filter = ['statut', 'en_service_actuel', 'ville', 'date_creation']
    search_fields = ['nom', 'code', 'ville', 'adresse', 'email']
    ordering = ['nom']
    list_per_page = 20

    fieldsets = (
        ('📋 Informations générales', {
            'fields': (('nom', 'code'), 'description', 'statut', 'en_service_actuel')
        }),
        ('📍 Localisation', {
            'fields': ('adresse', 'ville')
        }),
        ('📞 Contact', {
            'fields': (('telephone', 'email'),)
        }),
        ('🖼️ Images', {
            'fields': (('logo', 'image_couverture'),),
            'classes': ('collapse',),
        }),
    )
    readonly_fields = ['date_creation', 'date_modification']

    def logo_display(self, obj):
        if obj.logo:
            return format_html('<img src="{}" style="width:36px;height:36px;border-radius:8px;object-fit:cover;">', obj.logo.url)
        return format_html('<div style="width:36px;height:36px;border-radius:8px;background:#e8f5e9;display:flex;align-items:center;justify-content:center;font-size:16px;">🍽️</div>')
    logo_display.short_description = ''

    def statut_display(self, obj):
        colors = {'ACTIF': '#28a745', 'INACTIF': '#6c757d', 'SUSPENDU': '#dc3545'}
        color = colors.get(obj.statut, '#6c757d')
        return format_html('<span style="color:{};font-weight:600;">● {}</span>', color, obj.get_statut_display())
    statut_display.short_description = 'Statut'

    def nb_menus(self, obj):
        return format_html('<span style="font-weight:600;color:var(--primary-green);">{}</span>', obj.menus.count())
    nb_menus.short_description = 'Menus'

    actions = ['activer', 'desactiver', 'suspendre']

    def activer(self, request, queryset):
        n = queryset.update(statut='ACTIF')
        self.message_user(request, f'{n} restaurant(s) activé(s).')
    activer.short_description = '✅ Activer'

    def desactiver(self, request, queryset):
        n = queryset.update(statut='INACTIF')
        self.message_user(request, f'{n} restaurant(s) désactivé(s).')
    desactiver.short_description = '🚫 Désactiver'

    def suspendre(self, request, queryset):
        n = queryset.update(statut='SUSPENDU')
        self.message_user(request, f'{n} restaurant(s) suspendu(s).')
    suspendre.short_description = '⚠️ Suspendre'


@admin.register(PlanningRestaurant)
class PlanningRestaurantAdmin(admin.ModelAdmin):
    list_display = ['restaurant', 'agence', 'type_planning',
                    'periode_display', 'en_cours_display', 'est_actif', 'cree_par']
    list_filter = ['est_actif', 'type_planning', 'restaurant', 'agence', 'date_debut']
    search_fields = ['restaurant__nom', 'agence__nom']
    ordering = ['-date_debut']
    date_hierarchy = 'date_debut'

    fieldsets = (
        ('🏪 Affectation', {
            'fields': ('restaurant', 'agence')
        }),
        ('📅 Période', {
            'fields': ('type_planning', ('date_debut', 'date_fin'), 'est_actif')
        }),
        ('👤 Créé par', {
            'fields': ('cree_par',),
            'classes': ('collapse',),
        }),
    )
    readonly_fields = ['date_creation', 'date_modification']

    def periode_display(self, obj):
        return f"{obj.date_debut.strftime('%d/%m/%Y')} → {obj.date_fin.strftime('%d/%m/%Y')}"
    periode_display.short_description = 'Période'

    def en_cours_display(self, obj):
        if obj.est_actuel:
            return format_html('<span style="color:#28a745;font-weight:600;">● En cours</span>')
        return format_html('<span style="color:#adb5bd;">—</span>')
    en_cours_display.short_description = 'En cours'

    actions = ['activer_plannings', 'desactiver_plannings']

    def activer_plannings(self, request, queryset):
        n = queryset.update(est_actif=True)
        self.message_user(request, f'{n} planning(s) activé(s).')
    activer_plannings.short_description = '✅ Activer les plannings'

    def desactiver_plannings(self, request, queryset):
        n = queryset.update(est_actif=False)
        self.message_user(request, f'{n} planning(s) désactivé(s).')
    desactiver_plannings.short_description = '🚫 Désactiver les plannings'


@admin.register(Menu)
class MenuAdmin(admin.ModelAdmin):
    list_display = ['nom', 'restaurant', 'jour_semaine', 'date',
                    'prix', 'dispo_display', 'quantite_display']
    list_filter = ['est_disponible', 'jour_semaine', 'restaurant']
    search_fields = ['nom', 'restaurant__nom', 'plats']
    ordering = ['restaurant__nom', 'jour_semaine']

    fieldsets = (
        ('📋 Informations', {
            'fields': ('restaurant', ('nom', 'jour_semaine', 'date'), 'description', 'plats')
        }),
        ('💰 Tarif et stock', {
            'fields': ('prix', ('quantite_disponible', 'quantite_consomme'), 'est_disponible')
        }),
        ('🖼️ Image', {
            'fields': ('image',),
            'classes': ('collapse',),
        }),
    )

    def dispo_display(self, obj):
        if obj.est_disponible:
            return format_html('<span style="color:#28a745;font-weight:600;">● Disponible</span>')
        return format_html('<span style="color:#dc3545;font-weight:600;">● Indisponible</span>')
    dispo_display.short_description = 'Disponibilité'

    def quantite_display(self, obj):
        if obj.quantite_disponible is None:
            return format_html('<span style="color:#adb5bd;">Illimitée</span>')
        reste = obj.quantite_restante
        color = '#dc3545' if reste < 5 else '#28a745'
        return format_html('<span style="color:{};font-weight:600;">{}/{}</span>',
                           color, reste, obj.quantite_disponible)
    quantite_display.short_description = 'Stock'

    actions = ['rendre_disponible', 'rendre_indisponible']

    def rendre_disponible(self, request, queryset):
        n = queryset.update(est_disponible=True)
        self.message_user(request, f'{n} menu(s) rendu(s) disponible(s).')
    rendre_disponible.short_description = '✅ Rendre disponible'

    def rendre_indisponible(self, request, queryset):
        n = queryset.update(est_disponible=False)
        self.message_user(request, f'{n} menu(s) rendu(s) indisponible(s).')
    rendre_indisponible.short_description = '🚫 Rendre indisponible'


@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = ['client', 'restaurant', 'menu', 'date_reservation',
                    'statut_display', 'date_creation']
    list_filter = ['statut', 'date_reservation', 'restaurant']
    search_fields = ['client__prenom', 'client__nom', 'client__email', 'restaurant__nom']
    ordering = ['-date_reservation']
    date_hierarchy = 'date_reservation'
    readonly_fields = ['date_creation', 'date_modification']

    def statut_display(self, obj):
        colors = {
            'EN_ATTENTE': '#f59e0b', 'CONFIRME': '#28a745',
            'ANNULE': '#dc3545',     'TERMINE': '#6c757d',
        }
        color = colors.get(obj.statut, '#6c757d')
        return format_html('<span style="color:{};font-weight:600;">● {}</span>', color, obj.get_statut_display())
    statut_display.short_description = 'Statut'

    actions = ['confirmer', 'annuler_reservations']

    def confirmer(self, request, queryset):
        n = queryset.filter(statut='EN_ATTENTE').update(statut='CONFIRME')
        self.message_user(request, f'{n} réservation(s) confirmée(s).')
    confirmer.short_description = '✅ Confirmer les réservations'

    def annuler_reservations(self, request, queryset):
        n = queryset.exclude(statut='TERMINE').update(statut='ANNULE')
        self.message_user(request, f'{n} réservation(s) annulée(s).')
    annuler_reservations.short_description = '🚫 Annuler les réservations'

