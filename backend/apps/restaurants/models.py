"""
Modèles pour la gestion des restaurants partenaires, menus et réservations
"""
from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils import timezone


class Restaurant(models.Model):
    """Modèle pour les restaurants partenaires"""

    STATUT_CHOICES = [
        ('ACTIF', 'Actif'),
        ('INACTIF', 'Inactif'),
        ('SUSPENDU', 'Suspendu'),
    ]

    # Informations de base
    nom = models.CharField('Nom du restaurant', max_length=200)
    code = models.CharField('Code', max_length=20, unique=True)
    description = models.TextField('Description', blank=True)

    # Informations de contact
    adresse = models.TextField('Adresse')
    ville = models.CharField('Ville', max_length=100)
    telephone = models.CharField('Téléphone', max_length=17)
    email = models.EmailField('Email', blank=True)

    # Statut
    statut = models.CharField('Statut', max_length=20, choices=STATUT_CHOICES, default='ACTIF')
    en_service_actuel = models.BooleanField('En service actuellement', default=False)

    # Images
    logo = models.ImageField('Logo', upload_to='restaurants/logos/', blank=True, null=True)
    image_couverture = models.ImageField('Image de couverture', upload_to='restaurants/covers/', blank=True, null=True)

    # Horodatage
    date_creation = models.DateTimeField('Créé le', auto_now_add=True)
    date_modification = models.DateTimeField('Modifié le', auto_now=True)

    class Meta:
        verbose_name = 'Restaurant'
        verbose_name_plural = 'Restaurants'
        ordering = ['nom']

    def __str__(self):
        return f"{self.nom} ({self.code})"

    @property
    def plannings_actifs(self):
        """Retourne les plannings actuellement actifs"""
        maintenant = timezone.now()
        return self.plannings.filter(
            date_debut__lte=maintenant.date(),
            date_fin__gte=maintenant.date(),
            est_actif=True
        )

    def agences_servies(self):
        """Retourne la liste des agences actuellement servies"""
        return set([planning.agence for planning in self.plannings_actifs])


class PlanningRestaurant(models.Model):
    """Modèle pour les plannings de service des restaurants"""

    TYPE_PLANNING_CHOICES = [
        ('HEBDOMADAIRE', 'Hebdomadaire'),
        ('MENSUEL', 'Mensuel'),
    ]

    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name='plannings')
    agence = models.ForeignKey('accounts.Agence', on_delete=models.CASCADE, related_name='plannings_restaurant')

    type_planning = models.CharField('Type de planning', max_length=20, choices=TYPE_PLANNING_CHOICES)
    date_debut = models.DateField('Date de début')
    date_fin = models.DateField('Date de fin')

    est_actif = models.BooleanField('Actif', default=True)

    cree_par = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='plannings_crees',
        limit_choices_to={'type_utilisateur__in': ['SUPER_ADMIN', 'CASHIER']}
    )

    date_creation = models.DateTimeField('Créé le', auto_now_add=True)
    date_modification = models.DateTimeField('Modifié le', auto_now=True)

    class Meta:
        verbose_name = 'Planning de Restaurant'
        verbose_name_plural = 'Plannings de Restaurants'
        ordering = ['-date_debut']
        unique_together = ['restaurant', 'agence', 'date_debut', 'date_fin']

    def __str__(self):
        return f"{self.restaurant.nom} - {self.agence.nom} ({self.date_debut} à {self.date_fin})"

    def clean(self):
        """Validation du planning"""
        if self.date_debut > self.date_fin:
            raise ValidationError('La date de début doit être antérieure à la date de fin')

        chevauchement = PlanningRestaurant.objects.filter(
            restaurant=self.restaurant,
            agence=self.agence,
            est_actif=True
        ).exclude(pk=self.pk).filter(
            models.Q(date_debut__lte=self.date_fin) &
            models.Q(date_fin__gte=self.date_debut)
        )
        if chevauchement.exists():
            raise ValidationError('Ce planning chevauche un planning existant')

    @property
    def est_actuel(self):
        """Vérifie si le planning est actuellement actif"""
        aujourd_hui = timezone.now().date()
        return self.est_actif and self.date_debut <= aujourd_hui <= self.date_fin


class Menu(models.Model):
    """Modèle pour les menus quotidiens des restaurants"""

    JOUR_CHOICES = [
        ('LUNDI', 'Lundi'),
        ('MARDI', 'Mardi'),
        ('MERCREDI', 'Mercredi'),
        ('JEUDI', 'Jeudi'),
        ('VENDREDI', 'Vendredi'),
    ]

    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name='menus')

    jour_semaine = models.CharField('Jour de la semaine', max_length=20, choices=JOUR_CHOICES)
    date = models.DateField('Date', blank=True, null=True)

    nom = models.CharField('Nom du menu', max_length=200)
    description = models.TextField('Description', blank=True)
    plats = models.TextField('Plats')  # Liste des plats (CSV ou JSON)

    est_disponible = models.BooleanField('Disponible', default=True)
    quantite_disponible = models.IntegerField('Quantité disponible', default=0, blank=True, null=True)
    quantite_consomme = models.IntegerField('Quantité consommée', default=0)

    prix = models.DecimalField('Prix', max_digits=10, decimal_places=2, default=settings.TICKET_FULL_PRICE)

    image = models.ImageField('Image du plat', upload_to='menus/', blank=True, null=True)

    date_creation = models.DateTimeField('Créé le', auto_now_add=True)
    date_modification = models.DateTimeField('Modifié le', auto_now=True)

    class Meta:
        verbose_name = 'Menu'
        verbose_name_plural = 'Menus'
        ordering = ['restaurant', 'jour_semaine']

    def __str__(self):
        jour = dict(self.JOUR_CHOICES).get(self.jour_semaine, self.jour_semaine)
        return f"{self.restaurant.nom} - {jour}: {self.nom}"

    @property
    def quantite_restante(self):
        """Calcule la quantité restante"""
        if self.quantite_disponible is None:
            return None
        return max(0, self.quantite_disponible - self.quantite_consomme)

    def incrementer_consomme(self, quantite=1):
        """Incrémente la quantité consommée"""
        self.quantite_consomme += quantite
        if self.quantite_disponible and self.quantite_consomme >= self.quantite_disponible:
            self.est_disponible = False
        self.save()


class Reservation(models.Model):
    """Modèle pour les réservations de repas"""

    STATUT_CHOICES = [
        ('EN_ATTENTE', 'En attente'),
        ('CONFIRME', 'Confirmé'),
        ('ANNULE', 'Annulé'),
        ('TERMINE', 'Complété'),
    ]

    client = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='reservations',
        limit_choices_to={'type_utilisateur': 'CLIENT'}
    )

    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name='reservations')
    menu = models.ForeignKey(Menu, on_delete=models.CASCADE, related_name='reservations')

    date_reservation = models.DateField('Date de réservation')
    quantite = models.IntegerField('Quantité', default=1)

    statut = models.CharField('Statut', max_length=20, choices=STATUT_CHOICES, default='EN_ATTENTE')
    notes = models.TextField('Notes', blank=True)

    date_creation = models.DateTimeField('Créée le', auto_now_add=True)
    date_modification = models.DateTimeField('Modifiée le', auto_now=True)

    class Meta:
        verbose_name = 'Réservation'
        verbose_name_plural = 'Réservations'
        ordering = ['-date_reservation', '-date_creation']

    def __str__(self):
        return f"Réservation de {self.client.get_full_name()} - {self.menu.nom} ({self.date_reservation})"

    def clean(self):
        """Validation de la réservation"""
        if self.date_reservation < timezone.now().date():
            raise ValidationError('La date de réservation doit être dans le futur')
        if not self.menu.est_disponible:
            raise ValidationError('Ce menu n\'est pas disponible')

    def confirmer(self):
        """Confirmer la réservation"""
        self.statut = 'CONFIRME'
        self.save()

    def annuler(self):
        """Annuler la réservation"""
        self.statut = 'ANNULE'
        self.save()

    def terminer(self):
        """Marquer la réservation comme terminée"""
        self.statut = 'TERMINE'
        self.menu.incrementer_consomme(self.quantite)
        self.save()
