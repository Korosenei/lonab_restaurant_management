"""
Modèles pour la gestion des notifications et des templates d'email
"""
from django.db import models
from django.conf import settings
from django.utils import timezone


class Notification(models.Model):
    """Modèle pour les notifications des utilisateurs"""

    TYPES_NOTIFICATION = [
        ('COMPTE', 'Compte'),
        ('ACHAT', 'Achat'),
        ('CONSOMMATION', 'Consommation'),
        ('PROGRAMMATION', 'Programmation'),
        ('MENU', 'Menu'),
        ('SYSTEME', 'Système'),
        ('RAPPEL', 'Rappel'),
    ]

    PRIORITES = [
        ('BASSE', 'Basse'),
        ('MOYENNE', 'Moyenne'),
        ('HAUTE', 'Haute'),
        ('URGENTE', 'Urgente'),
    ]

    destinataire = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifs'
    )

    # Détails de la notification
    type_notification = models.CharField('Type', max_length=20, choices=TYPES_NOTIFICATION)
    priorite = models.CharField('Priorité', max_length=10, choices=PRIORITES, default='MOYENNE')

    titre = models.CharField('Titre', max_length=200)
    message = models.TextField('Message')

    # Lien optionnel
    lien = models.URLField('Lien', blank=True)
    texte_lien = models.CharField('Texte du lien', max_length=100, blank=True)

    # Statut
    est_lu = models.BooleanField('Lu', default=False)
    lu_le = models.DateTimeField('Lu le', null=True, blank=True)

    # Notification par email
    envoyer_email = models.BooleanField('Envoyer par email', default=False)
    email_envoye = models.BooleanField('Email envoyé', default=False)
    email_envoye_le = models.DateTimeField('Email envoyé le', null=True, blank=True)

    # Notification par SMS
    envoyer_sms = models.BooleanField('Envoyer par SMS', default=False)
    sms_envoye = models.BooleanField('SMS envoyé', default=False)
    sms_envoye_le = models.DateTimeField('SMS envoyé le', null=True, blank=True)

    # Objets liés
    modele_lie = models.CharField('Modèle lié', max_length=100, blank=True)
    id_lie = models.IntegerField('ID lié', null=True, blank=True)

    # Horodatage
    cree_le = models.DateTimeField('Créé le', auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = 'Notification'
        verbose_name_plural = 'Notifications'
        ordering = ['-cree_le']
        indexes = [
            models.Index(fields=['destinataire', 'est_lu']),
            models.Index(fields=['cree_le']),
        ]

    def __str__(self):
        return f"{self.titre} - {self.destinataire.get_full_name()}"

    def marquer_comme_lu(self):
        """Marquer la notification comme lue"""
        if not self.est_lu:
            self.est_lu = True
            self.lu_le = timezone.now()
            self.save(update_fields=['est_lu', 'lu_le'])

    def envoyer_email_notification(self):
        """Envoyer la notification par email"""
        if self.envoyer_email and not self.email_envoye:
            from django.core.mail import send_mail

            try:
                send_mail(
                    subject=self.titre,
                    message=self.message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[self.destinataire.email],
                    fail_silently=False,
                )
                self.email_envoye = True
                self.email_envoye_le = timezone.now()
                self.save(update_fields=['email_envoye', 'email_envoye_le'])
                return True
            except Exception as e:
                print(f"Erreur d'envoi d'email : {e}")
                return False
        return False


class ModeleEmail(models.Model):
    """Modèle pour les templates d'email"""

    TYPES_MODELE = [
        ('BIENVENUE', 'Bienvenue'),
        ('CONFIRMATION_ACHAT', 'Confirmation d\'achat'),
        ('CONFIRMATION_CONSOMMATION', 'Confirmation de consommation'),
        ('NOTIFICATION_PROGRAMMATION', 'Notification de programmation'),
        ('NOTIFICATION_MENU', 'Notification de menu'),
        ('REINITIALISATION_MDP', 'Réinitialisation de mot de passe'),
        ('VERIFICATION_COMPTE', 'Vérification de compte'),
        ('PERSONNALISE', 'Personnalisé'),
    ]

    nom = models.CharField('Nom', max_length=200, unique=True)
    type_modele = models.CharField('Type', max_length=50, choices=TYPES_MODELE)

    # Contenu du template
    sujet = models.CharField('Sujet', max_length=200)
    corps_texte = models.TextField('Corps (texte)')
    corps_html = models.TextField('Corps (HTML)', blank=True)

    # Variables disponibles dans le template
    variables_disponibles = models.JSONField('Variables disponibles', default=dict)

    # Statut
    actif = models.BooleanField('Actif', default=True)

    # Horodatage
    cree_le = models.DateTimeField('Créé le', auto_now_add=True)
    modifie_le = models.DateTimeField('Modifié le', auto_now=True)

    class Meta:
        verbose_name = 'Modèle d\'Email'
        verbose_name_plural = 'Modèles d\'Email'
        ordering = ['nom']

    def __str__(self):
        return f"{self.nom} ({self.get_type_modele_display()})"

    def rendre(self, contexte):
        """Rendre le template avec le contexte"""
        from django.template import Context, Template

        sujet_template = Template(self.sujet)
        corps_template = Template(self.corps_texte)

        rendu_sujet = sujet_template.render(Context(contexte))
        rendu_corps = corps_template.render(Context(contexte))

        return rendu_sujet, rendu_corps
