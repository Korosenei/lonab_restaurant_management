"""
Modèles pour la gestion des tickets
"""
from django.db import models
from django.utils import timezone
from django.conf import settings
from django.core.exceptions import ValidationError
from datetime import datetime, timedelta
import qrcode
from io import BytesIO
from django.core.files import File
import hashlib
import json


class Ticket(models.Model):
    """Modèle pour un ticket individuel"""

    STATUT_CHOICES = [
        ('DISPONIBLE', 'Disponible'),
        ('CONSOMME', 'Consommé'),
        ('EXPIRE', 'Expiré'),
        ('ANNULE', 'Annulé'),
    ]

    # Informations du ticket
    numero_ticket = models.CharField('Numéro du ticket', max_length=50, unique=True, db_index=True)
    proprietaire = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='tickets',
        limit_choices_to={'type_utilisateur': 'CLIENT'}
    )

    # Référence de transaction
    transaction = models.ForeignKey(
        'transactions.TransactionTicket',
        on_delete=models.CASCADE,
        related_name='tickets_genere'
    )

    # Statut
    statut = models.CharField('Statut', max_length=20, choices=STATUT_CHOICES, default='DISPONIBLE')

    # Détails de consommation
    date_consommation = models.DateTimeField('Consommé le', blank=True, null=True)
    restaurant_consommateur = models.ForeignKey(
        'restaurants.Restaurant',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tickets_consommes'
    )
    valide_par = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tickets_valides',
        limit_choices_to={'type_utilisateur': 'GESTIONNAIRE_RESTAURANT'}
    )

    # Validité
    valide_de = models.DateField('Valide à partir du')
    valide_jusqua = models.DateField('Valide jusqu\'au')

    # Aspect financier
    prix_paye = models.DecimalField('Prix payé', max_digits=10, decimal_places=2, default=settings.TICKET_PRICE)
    montant_subventionne = models.DecimalField('Montant subventionné', max_digits=10, decimal_places=2,
                                               default=settings.TICKET_SUBSIDY)

    # Horodatage
    date_creation = models.DateTimeField('Créé le', auto_now_add=True)
    date_modification = models.DateTimeField('Modifié le', auto_now=True)

    class Meta:
        verbose_name = 'Ticket'
        verbose_name_plural = 'Tickets'
        ordering = ['-date_creation']
        indexes = [
            models.Index(fields=['numero_ticket']),
            models.Index(fields=['proprietaire', 'statut']),
            models.Index(fields=['valide_de', 'valide_jusqua']),
        ]

    def __str__(self):
        return f"Ticket {self.numero_ticket} - {self.proprietaire.get_full_name()}"

    def clean(self):
        """Validation du ticket"""
        if self.valide_de and self.valide_jusqua:
            if self.valide_de > self.valide_jusqua:
                raise ValidationError('La date de début doit être antérieure à la date de fin')

    @property
    def est_valide(self):
        """Vérifie si le ticket est valide pour utilisation"""
        aujourd_hui = timezone.now().date()
        return (
                self.statut == 'DISPONIBLE' and
                self.valide_de <= aujourd_hui <= self.valide_jusqua
        )

    @property
    def est_expire(self):
        """Vérifie si le ticket est expiré"""
        return timezone.now().date() > self.valide_jusqua

    def marquer_comme_consomme(self, restaurant, gestionnaire):
        """Marquer le ticket comme consommé"""
        if not self.est_valide:
            raise ValidationError('Ce ticket n\'est pas valide pour consommation')

        self.statut = 'CONSOMME'
        self.date_consommation = timezone.now()
        self.restaurant_consommateur = restaurant
        self.valide_par = gestionnaire
        self.save()

    def annuler(self):
        """Annuler le ticket"""
        if self.statut == 'CONSOMME':
            raise ValidationError('Un ticket consommé ne peut pas être annulé')

        self.statut = 'ANNULE'
        self.save()


class CodeQR(models.Model):
    """Modèle pour les codes QR générés pour la consommation des tickets"""

    utilisateur = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='codes_qr',
        limit_choices_to={'type_utilisateur': 'CLIENT'}
    )

    # Données QR
    code = models.CharField('Code', max_length=255, unique=True, db_index=True)
    image_qr = models.ImageField('Image QR', upload_to='qrcodes/', blank=True, null=True)

    # Tickets inclus dans ce QR
    donnees_tickets = models.JSONField('Données des tickets', default=dict)

    # Validité
    est_valide = models.BooleanField('Valide', default=True)
    expire_le = models.DateTimeField('Expire le')

    # Utilisation
    est_utilise = models.BooleanField('Utilisé', default=False)
    utilise_le = models.DateTimeField('Utilisé le', blank=True, null=True)
    utilise_par_restaurant = models.ForeignKey(
        'restaurants.Restaurant',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='codes_qr_scannes'
    )

    # Horodatage
    date_creation = models.DateTimeField('Créé le', auto_now_add=True)

    class Meta:
        verbose_name = 'Code QR'
        verbose_name_plural = 'Codes QR'
        ordering = ['-date_creation']
        indexes = [
            models.Index(fields=['code']),
            models.Index(fields=['utilisateur', 'est_valide']),
            models.Index(fields=['expire_le']),
        ]

    def __str__(self):
        return f"Code QR {self.code[:10]}... - {self.utilisateur.get_full_name()}"

    def save(self, *args, **kwargs):
        """Générer un code QR à la sauvegarde"""
        if not self.code:
            # Générer un code unique
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            data = f"{self.utilisateur.id}_{timestamp}_{self.utilisateur.email}"
            self.code = hashlib.sha256(data.encode()).hexdigest()

        if not self.expire_le:
            # Définir la date d'expiration
            self.expire_le = timezone.now() + timedelta(minutes=settings.QR_CODE_EXPIRY_MINUTES)

        super().save(*args, **kwargs)

        # Générer l'image du QR code
        if not self.image_qr:
            self.generer_image_qr()

    def generer_image_qr(self):
        """Générer l'image du QR code"""
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )

        # Données à encoder
        qr_data = {
            'code': self.code,
            'utilisateur_id': self.utilisateur.id,
            'email': self.utilisateur.email,
            'cree_le': self.date_creation.isoformat() if self.date_creation else timezone.now().isoformat(),
            'expire_le': self.expire_le.isoformat(),
        }

        qr.add_data(json.dumps(qr_data))
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")

        # Sauvegarder dans le fichier
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        nom_fichier = f'qr_{self.utilisateur.id}_{timezone.now().strftime("%Y%m%d%H%M%S")}.png'
        self.image_qr.save(nom_fichier, File(buffer), save=False)
        self.save(update_fields=['image_qr'])

    def verifier_validite(self):
        """Vérifier si le code QR est toujours valide"""
        maintenant = timezone.now()

        if not self.est_valide:
            return False, "Code QR invalide"

        if self.est_utilise:
            return False, "Code QR déjà utilisé"

        if maintenant > self.expire_le:
            self.est_valide = False
            self.save()
            return False, "Code QR expiré"

        # Vérifier si l'utilisateur a des tickets valides
        tickets_valides = Ticket.objects.filter(
            proprietaire=self.utilisateur,
            statut='DISPONIBLE',
            valide_de__lte=maintenant.date(),
            valide_jusqua__gte=maintenant.date()
        )

        if not tickets_valides.exists():
            return False, "Aucun ticket valide disponible"

        return True, "Code QR valide"

    def marquer_comme_utilise(self, restaurant):
        """Marquer le code QR comme utilisé"""
        self.est_utilise = True
        self.utilise_le = timezone.now()
        self.utilise_par_restaurant = restaurant
        self.est_valide = False
        self.save()

    @classmethod
    def invalider_codes_precedents(cls, utilisateur):
        """Invalider tous les codes QR précédents pour un utilisateur"""
        cls.objects.filter(
            utilisateur=utilisateur,
            est_valide=True,
            est_utilise=False
        ).update(est_valide=False)

