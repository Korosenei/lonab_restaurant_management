"""
Modèles pour les paramètres système et configurations
"""
from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone


class ParametresSysteme(models.Model):
    """Modèle pour les paramètres globaux du système"""

    # Paramètres des tickets
    tickets_min_par_transaction = models.IntegerField(
        'Nombre minimum de tickets par transaction',
        default=1,
        help_text='Nombre minimum de tickets pouvant être achetés en une transaction'
    )

    tickets_max_par_transaction = models.IntegerField(
        'Nombre maximum de tickets par transaction',
        default=20,
        help_text='Nombre maximum de tickets pouvant être achetés en une transaction'
    )

    transactions_max_par_mois = models.IntegerField(
        'Nombre maximum de transactions par mois',
        default=1,
        help_text='Nombre maximum de transactions qu\'un client peut effectuer par mois'
    )

    # Tarification
    prix_ticket = models.DecimalField(
        'Prix du ticket',
        max_digits=10,
        decimal_places=2,
        default=500,
        help_text='Prix payé par l\'employé pour un ticket'
    )

    prix_repas_complet = models.DecimalField(
        'Prix complet du repas',
        max_digits=10,
        decimal_places=2,
        default=2000,
        help_text='Prix complet d\'un repas'
    )

    subvention_ticket = models.DecimalField(
        'Montant de la subvention',
        max_digits=10,
        decimal_places=2,
        default=1500,
        help_text='Montant subventionné par la mutuelle par ticket'
    )

    # Paramètres QR Code
    duree_validite_qr_code_minutes = models.IntegerField(
        'Durée de validité du QR code (minutes)',
        default=3,
        help_text='Durée en minutes avant expiration d\'un QR code'
    )

    # Programmation des restaurants
    autoriser_programmation_hebdomadaire = models.BooleanField(
        'Autoriser programmation hebdomadaire',
        default=True
    )

    autoriser_programmation_mensuelle = models.BooleanField(
        'Autoriser programmation mensuelle',
        default=True
    )

    jours_avance_min_programmation = models.IntegerField(
        'Jours d\'avance minimum pour programmation',
        default=1,
        help_text='Nombre de jours d\'avance requis pour programmer un restaurant'
    )

    # Paramètres de notifications
    envoyer_notifications_achat = models.BooleanField(
        'Envoyer notifications d\'achat',
        default=True
    )

    envoyer_notifications_consommation = models.BooleanField(
        'Envoyer notifications de consommation',
        default=True
    )

    envoyer_notifications_programmation = models.BooleanField(
        'Envoyer notifications de programmation',
        default=True
    )

    envoyer_notifications_menu = models.BooleanField(
        'Envoyer notifications de menu',
        default=True
    )

    # Email
    email_notifications_expediteur = models.EmailField(
        'Email d\'envoi des notifications',
        default='noreply@lonab.com'
    )

    # Informations sur l'entreprise
    nom_entreprise = models.CharField(
        'Nom de l\'entreprise',
        max_length=200,
        default='LONAB'
    )

    nom_mutuelle = models.CharField(
        'Nom de la mutuelle',
        max_length=200,
        default='MUTRALO'
    )

    email_support = models.EmailField(
        'Email de support',
        default='support@lonab.com'
    )

    telephone_support = models.CharField(
        'Téléphone de support',
        max_length=17,
        blank=True
    )

    # Mode maintenance
    mode_maintenance = models.BooleanField(
        'Mode maintenance',
        default=False,
        help_text='Active le mode maintenance (accès limité)'
    )

    message_maintenance = models.TextField(
        'Message de maintenance',
        blank=True,
        help_text='Message affiché pendant la maintenance'
    )

    # Horodatage
    cree_le = models.DateTimeField('Créé le', auto_now_add=True)
    modifie_le = models.DateTimeField('Modifié le', auto_now=True)
    modifie_par = models.ForeignKey(
        'accounts.Utilisateur',
        on_delete=models.SET_NULL,
        null=True,
        related_name='parametres_modifies'
    )

    class Meta:
        verbose_name = 'Paramètres Système'
        verbose_name_plural = 'Paramètres Système'

    def __str__(self):
        return f"Paramètres Système (Mis à jour: {self.modifie_le})"

    def save(self, *args, **kwargs):
        """S'assurer qu'il n'existe qu'une seule instance"""
        self.pk = 1
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        """Empêcher la suppression"""
        raise ValidationError('Les paramètres système ne peuvent pas être supprimés')

    @classmethod
    def charger(cls):
        """Charger ou créer les paramètres système"""
        obj, cree = cls.objects.get_or_create(pk=1)
        return obj

    def clean(self):
        """Validation des paramètres"""
        if self.tickets_min_par_transaction < 1:
            raise ValidationError('Le minimum de tickets doit être au moins 1')

        if self.tickets_max_par_transaction < self.tickets_min_par_transaction:
            raise ValidationError(
                'Le maximum de tickets doit être supérieur ou égal au minimum'
            )

        if self.prix_ticket < 0:
            raise ValidationError('Le prix du ticket ne peut pas être négatif')

        if self.subvention_ticket > self.prix_repas_complet:
            raise ValidationError(
                'La subvention ne peut pas être supérieure au prix complet'
            )

        if self.prix_ticket + self.subvention_ticket != self.prix_repas_complet:
            raise ValidationError(
                'La somme du prix payé et de la subvention doit égaler le prix complet'
            )


class JourFerie(models.Model):
    """Modèle pour les jours fériés (restaurants fermés)"""

    nom = models.CharField('Nom du jour férié', max_length=200)
    date = models.DateField('Date')
    recurrent = models.BooleanField('Récurrent chaque année', default=False)
    description = models.TextField('Description', blank=True)

    actif = models.BooleanField('Actif', default=True)

    cree_le = models.DateTimeField('Créé le', auto_now_add=True)
    modifie_le = models.DateTimeField('Modifié le', auto_now=True)

    class Meta:
        verbose_name = 'Jour Férié'
        verbose_name_plural = 'Jours Fériés'
        ordering = ['date']

    def __str__(self):
        return f"{self.nom} - {self.date}"


class JournalAudit(models.Model):
    """Modèle pour le journal d'audit système"""

    ACTIONS = [
        ('CREATION', 'Création'),
        ('MODIFICATION', 'Modification'),
        ('SUPPRESSION', 'Suppression'),
        ('CONNEXION', 'Connexion'),
        ('DECONNEXION', 'Déconnexion'),
        ('ACHAT', 'Achat'),
        ('CONSOMMATION', 'Consommation'),
        ('REMBOURSEMENT', 'Remboursement'),
    ]

    utilisateur = models.ForeignKey(
        'accounts.Utilisateur',
        on_delete=models.SET_NULL,
        null=True,
        related_name='journaux_audit'
    )

    action = models.CharField('Action', max_length=20, choices=ACTIONS)
    modele = models.CharField('Modèle', max_length=100)
    objet_id = models.IntegerField('ID de l\'objet', null=True, blank=True)

    description = models.TextField('Description')
    adresse_ip = models.GenericIPAddressField('Adresse IP', null=True, blank=True)
    user_agent = models.TextField('User Agent', blank=True)

    donnees_anciennes = models.JSONField('Anciennes données', null=True, blank=True)
    donnees_nouvelles = models.JSONField('Nouvelles données', null=True, blank=True)

    cree_le = models.DateTimeField('Créé le', auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = 'Journal d\'Audit'
        verbose_name_plural = 'Journaux d\'Audit'
        ordering = ['-cree_le']
        indexes = [
            models.Index(fields=['utilisateur', 'cree_le']),
            models.Index(fields=['action', 'cree_le']),
            models.Index(fields=['modele', 'objet_id']),
        ]

    def __str__(self):
        nom_utilisateur = self.utilisateur.get_full_name() if self.utilisateur else 'Système'
        return f"{nom_utilisateur} - {self.get_action_display()} - {self.cree_le}"
