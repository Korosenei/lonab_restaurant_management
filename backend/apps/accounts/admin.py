"""
Configuration de l'administration pour l'application comptes
"""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import Utilisateur, Direction, Agence, ProfilUtilisateur


@admin.register(Utilisateur)
class UserAdmin(BaseUserAdmin):
    """Administration pour le modèle Utilisateur"""

    list_display = ['email', 'get_full_name', 'type_utilisateur', 'direction', 'agence', 'est_actif', 'est_verifie', 'date_inscription']
    list_filter = ['type_utilisateur', 'est_actif', 'est_verifie', 'est_personnel', 'direction', 'agence', 'date_inscription']
    search_fields = ['email', 'prenom', 'nom', 'matricule', 'nom_utilisateur']
    ordering = ['-date_inscription']

    fieldsets = (
        ('Informations de connexion', {
            'fields': ('email', 'password')
        }),
        ('Informations personnelles', {
            'fields': ('prenom', 'nom', 'telephone', 'genre', 'date_naissance', 'photo_profil', 'adresse')
        }),
        ('Type et affectation', {
            'fields': ('type_utilisateur', 'matricule', 'departement', 'poste', 'direction', 'agence', 'superieur_hierarchique', 'restaurant_gere')
        }),
        ('Permissions', {
            'fields': ('est_actif', 'est_personnel', 'est_super_utilisateur', 'est_verifie', 'groups', 'user_permissions')
        }),
        ('Dates importantes', {
            'fields': ('derniere_connexion', 'date_inscription')
        }),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'prenom', 'nom', 'type_utilisateur', 'direction', 'agence', 'password1', 'password2'),
        }),
    )

    readonly_fields = ['date_inscription', 'derniere_connexion']

    def get_full_name(self, obj):
        """Afficher le nom complet"""
        return obj.get_full_name()
    get_full_name.short_description = 'Nom complet'


@admin.register(Direction)
class DirectionAdmin(admin.ModelAdmin):
    """Administration pour le modèle Direction"""

    list_display = ['nom', 'code', 'directeur', 'total_employes', 'employes_actifs', 'est_active', 'date_creation']
    list_filter = ['est_active', 'date_creation']
    search_fields = ['nom', 'code', 'description']
    ordering = ['nom']

    fieldsets = (
        ('Informations générales', {
            'fields': ('nom', 'code', 'description')
        }),
        ('Contact', {
            'fields': ('telephone', 'email')
        }),
        ('Responsable', {
            'fields': ('directeur',)
        }),
        ('Statut', {
            'fields': ('est_active',)
        }),
    )

    readonly_fields = ['date_creation', 'date_modification']

    def total_employes(self, obj):
        """Afficher le total des employés"""
        return obj.total_employes
    total_employes.short_description = 'Total employés'

    def employes_actifs(self, obj):
        """Afficher les employés actifs"""
        return obj.employes_actifs
    employes_actifs.short_description = 'Employés actifs'


@admin.register(Agence)
class AgenceAdmin(admin.ModelAdmin):
    """Administration pour le modèle Agence"""

    list_display = ['nom', 'code', 'type_agence', 'direction', 'ville', 'responsable', 'total_employes', 'est_active', 'date_creation']
    list_filter = ['est_active', 'type_agence', 'direction', 'ville', 'date_creation']
    search_fields = ['nom', 'code', 'ville', 'adresse', 'region']
    ordering = ['nom']

    fieldsets = (
        ('Informations générales', {
            'fields': ('nom', 'code', 'type_agence', 'description')
        }),
        ('Localisation', {
            'fields': ('adresse', 'ville', 'region', 'code_postal')
        }),
        ('Contact', {
            'fields': ('telephone', 'email', 'fax')
        }),
        ('Hiérarchie', {
            'fields': ('direction', 'agence_parente', 'responsable')
        }),
        ('Capacité et statut', {
            'fields': ('capacite_max_employes', 'est_active', 'date_ouverture', 'date_fermeture')
        }),
        ('Autres', {
            'fields': ('notes',)
        }),
    )

    readonly_fields = ['date_creation', 'date_modification']

    def description(self, obj):
        """Afficher une description courte"""
        return f"{obj.get_type_agence_display()} - {obj.ville}"
    description.short_description = 'Description'

    def total_employes(self, obj):
        """Afficher le total des employés"""
        count = obj.total_employes
        capacite = obj.capacite_max_employes or '∞'
        return f"{count}/{capacite}"
    total_employes.short_description = 'Employés'

    def has_capacity(self, obj):
        """Afficher si l'agence a de la capacité"""
        return obj.a_capacite
    has_capacity.short_description = 'Capacité disponible'
    has_capacity.boolean = True


@admin.register(ProfilUtilisateur)
class ProfilUtilisateurAdmin(admin.ModelAdmin):
    """Administration pour le modèle Profil Utilisateur"""

    list_display = ['utilisateur', 'notification_email', 'notification_sms', 'langue']
    list_filter = ['notification_email', 'notification_sms', 'langue']
    search_fields = ['utilisateur__email', 'utilisateur__prenom', 'utilisateur__nom']

    fieldsets = (
        ('Utilisateur', {
            'fields': ('utilisateur',)
        }),
        ('Préférences', {
            'fields': ('notification_email', 'notification_sms', 'langue')
        }),
        ('Contact d\'urgence', {
            'fields': ('contact_urgence_nom', 'contact_urgence_telephone')
        }),
        ('Autres', {
            'fields': ('notes',)
        }),
    )