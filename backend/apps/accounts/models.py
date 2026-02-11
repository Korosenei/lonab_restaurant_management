"""
Modèles pour les comptes utilisateurs et l'authentification
"""
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone
from django.core.validators import RegexValidator


class GestionnaireUtilisateur(BaseUserManager):
    """Gestionnaire personnalisé des utilisateurs"""

    def creer_utilisateur(self, email, mot_de_passe=None, **champs_supplementaires):
        """Créer et retourner un utilisateur standard"""
        if not email:
            raise ValueError("L'adresse email est obligatoire")

        email = self.normalize_email(email)
        utilisateur = self.model(email=email, **champs_supplementaires)
        utilisateur.set_password(mot_de_passe)
        utilisateur.save(using=self._db)
        return utilisateur

    def creer_super_utilisateur(self, email, mot_de_passe=None, **champs_supplementaires):
        """Créer et retourner un super administrateur"""
        champs_supplementaires.setdefault('est_personnel', True)
        champs_supplementaires.setdefault('est_super_utilisateur', True)
        champs_supplementaires.setdefault('est_actif', True)
        champs_supplementaires.setdefault('type_utilisateur', 'SUPER_ADMIN')

        if champs_supplementaires.get('est_personnel') is not True:
            raise ValueError("Le super utilisateur doit avoir est_personnel=True.")
        if champs_supplementaires.get('est_super_utilisateur') is not True:
            raise ValueError("Le super utilisateur doit avoir est_super_utilisateur=True.")

        return self.creer_utilisateur(email, mot_de_passe, **champs_supplementaires)

    # Aliases anglais pour Django
    create_user = creer_utilisateur
    create_superuser = creer_super_utilisateur


class Utilisateur(AbstractBaseUser, PermissionsMixin):
    """Modèle Utilisateur personnalisé"""

    TYPES_UTILISATEUR = [
        ('CLIENT', 'Client (Employé)'),
        ('CAISSIER', 'Caissier'),
        ('GESTIONNAIRE_RESTAURANT', 'Gestionnaire de restaurant'),
        ('SUPER_ADMIN', 'Super administrateur'),
    ]

    GENRES = [
        ('M', 'Masculin'),
        ('F', 'Féminin'),
    ]

    validateur_telephone = RegexValidator(
        regex=r'^\+?1?\d{8,15}$',
        message="Le numéro de téléphone doit être au format: '+999999999'. 8 à 15 chiffres autorisés."
    )

    # Informations de base
    email = models.EmailField("Adresse email", unique=True, db_index=True)
    nom_utilisateur = models.CharField("Nom d'utilisateur", max_length=150, unique=True, blank=True, null=True)
    prenom = models.CharField("Prénom", max_length=100)
    nom = models.CharField("Nom", max_length=100)
    telephone = models.CharField("Téléphone", validators=[validateur_telephone], max_length=17, blank=True)
    genre = models.CharField("Genre", max_length=1, choices=GENRES, blank=True)
    date_naissance = models.DateField("Date de naissance", blank=True, null=True)

    # Type d'utilisateur
    type_utilisateur = models.CharField(
        "Type d'utilisateur",
        max_length=30,
        choices=TYPES_UTILISATEUR,
        default='CLIENT'
    )

    # Informations employé spécifiques (pour type CLIENT)
    matricule = models.CharField("Matricule", max_length=50, unique=True, blank=True, null=True, db_index=True)
    departement = models.CharField("Département", max_length=100, blank=True)
    poste = models.CharField("Poste", max_length=100, blank=True)

    # Hiérarchie - Direction et Agence
    direction = models.ForeignKey(
        'Direction',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='employes',
        verbose_name='Direction'
    )
    agence = models.ForeignKey(
        'Agence',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='employes',
        verbose_name='Agence'
    )

    # Hiérarchie supérieur/subordonné
    superieur_hierarchique = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='subordonnes',
        verbose_name='Supérieur hiérarchique'
    )

    # Gestionnaire de restaurant spécifique
    restaurant_gere = models.ForeignKey(
        'restaurants.Restaurant',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='gestionnaires'
    )

    # Profil
    photo_profil = models.ImageField("Photo de profil", upload_to='profils/', blank=True, null=True)
    adresse = models.TextField("Adresse", blank=True)

    # Statut
    est_actif = models.BooleanField("Actif", default=True)
    est_personnel = models.BooleanField("Personnel", default=False)
    est_verifie = models.BooleanField("Vérifié", default=False)
    est_super_utilisateur = models.BooleanField("Super utilisateur", default=False)

    # Dates
    date_inscription = models.DateTimeField("Date d'inscription", default=timezone.now)
    derniere_connexion = models.DateTimeField("Dernière connexion", blank=True, null=True)
    date_modification = models.DateTimeField("Modifié le", auto_now=True)

    # Manager
    objects = GestionnaireUtilisateur()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['prenom', 'nom']

    class Meta:
        verbose_name = "Utilisateur"
        verbose_name_plural = "Utilisateurs"
        ordering = ['-date_inscription']
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['matricule']),
            models.Index(fields=['type_utilisateur']),
        ]

    def __str__(self):
        return f"{self.prenom} {self.nom} ({self.get_type_utilisateur_display()})"

    def get_full_name(self):
        """Retourne le nom complet de l'utilisateur"""
        return f"{self.prenom} {self.nom}".strip()

    def get_short_name(self):
        """Retourne le prénom de l'utilisateur"""
        return self.prenom

    def save(self, *args, **kwargs):
        """Surcharge de la sauvegarde pour générer le nom d'utilisateur depuis l'email si non fourni"""
        if not self.nom_utilisateur:
            self.nom_utilisateur = self.email.split('@')[0]
        super().save(*args, **kwargs)

    # CORRECTION : Propriétés avec setters pour Django Admin
    @property
    def is_staff(self):
        """Requis par Django Admin"""
        return self.est_personnel

    @is_staff.setter
    def is_staff(self, value):
        """Permet de définir est_personnel via is_staff"""
        self.est_personnel = value

    @property
    def is_active(self):
        """Requis par Django"""
        return self.est_actif

    @is_active.setter
    def is_active(self, value):
        """Permet de définir est_actif via is_active"""
        self.est_actif = value

    @property
    def is_superuser(self):
        """Requis par Django Admin"""
        return self.est_super_utilisateur

    @is_superuser.setter
    def is_superuser(self, value):
        """Permet de définir est_super_utilisateur via is_superuser"""
        self.est_super_utilisateur = value

    @property
    def est_client(self):
        """Vérifie si l'utilisateur est un client"""
        return self.type_utilisateur == 'CLIENT'

    @property
    def est_caissier(self):
        """Vérifie si l'utilisateur est un caissier"""
        return self.type_utilisateur == 'CAISSIER'

    @property
    def est_gestionnaire_restaurant(self):
        """Vérifie si l'utilisateur est un gestionnaire de restaurant"""
        return self.type_utilisateur == 'GESTIONNAIRE_RESTAURANT'

    @property
    def est_super_admin(self):
        """Vérifie si l'utilisateur est un super administrateur"""
        return self.type_utilisateur == 'SUPER_ADMIN'


class Direction(models.Model):
    """Modèle pour les directions LONAB (départements)"""

    nom = models.CharField("Nom de la direction", max_length=200, unique=True)
    code = models.CharField("Code", max_length=20, unique=True)
    description = models.TextField("Description", blank=True)

    # Informations de contact
    telephone = models.CharField("Téléphone", max_length=17, blank=True)
    email = models.EmailField("Email", blank=True)

    # Directeur
    directeur = models.ForeignKey(
        Utilisateur,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='directions_dirigees',
        limit_choices_to={'type_utilisateur__in': ['SUPER_ADMIN']}
    )

    # Statut
    est_active = models.BooleanField("Active", default=True)

    # Dates
    date_creation = models.DateTimeField("Créée le", auto_now_add=True)
    date_modification = models.DateTimeField("Modifiée le", auto_now=True)

    class Meta:
        verbose_name = "Direction"
        verbose_name_plural = "Directions"
        ordering = ['nom']

    def __str__(self):
        return f"{self.nom} ({self.code})"

    @property
    def total_employes(self):
        """Obtenir le nombre total d'employés dans cette direction"""
        return Utilisateur.objects.filter(direction=self, type_utilisateur='CLIENT').count()

    @property
    def employes_actifs(self):
        """Obtenir le nombre d'employés actifs dans cette direction"""
        return Utilisateur.objects.filter(direction=self, type_utilisateur='CLIENT', est_actif=True).count()


class Agence(models.Model):
    """Modèle pour les agences LONAB"""

    TYPES_AGENCE = [
        ('SIEGE', 'Siège'),
        ('REGIONALE', 'Agence Régionale'),
        ('LOCALE', 'Agence Locale'),
        ('SUCCURSALE', 'Succursale'),
    ]

    nom = models.CharField("Nom de l'agence", max_length=200, unique=True)
    code = models.CharField("Code", max_length=20, unique=True)
    type_agence = models.CharField("Type d'agence", max_length=20, choices=TYPES_AGENCE, default='LOCALE')

    # Informations de localisation
    adresse = models.TextField("Adresse")
    ville = models.CharField("Ville", max_length=100)
    region = models.CharField("Région", max_length=100, blank=True)
    code_postal = models.CharField("Code postal", max_length=10, blank=True)

    # Informations de contact
    telephone = models.CharField("Téléphone", max_length=17)
    email = models.EmailField("Email", blank=True)
    fax = models.CharField("Fax", max_length=17, blank=True)

    # Hiérarchie - Direction parente
    direction = models.ForeignKey(
        Direction,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='agences',
        verbose_name='Direction'
    )

    # Agence parente (pour structure hiérarchique)
    agence_parente = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sous_agences',
        verbose_name='Agence parente'
    )

    # Responsable
    responsable = models.ForeignKey(
        Utilisateur,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='agences_gerees',
        limit_choices_to={'type_utilisateur__in': ['SUPER_ADMIN', 'CAISSIER']},
        verbose_name='Responsable'
    )

    # Capacité
    capacite_max_employes = models.IntegerField("Capacité maximale d'employés", default=100, blank=True, null=True)

    # Statut
    est_active = models.BooleanField("Active", default=True)
    date_ouverture = models.DateField("Date d'ouverture", blank=True, null=True)
    date_fermeture = models.DateField("Date de fermeture", blank=True, null=True)

    # Notes
    notes = models.TextField("Notes", blank=True)

    # Dates
    date_creation = models.DateTimeField("Créée le", auto_now_add=True)
    date_modification = models.DateTimeField("Modifiée le", auto_now=True)

    class Meta:
        verbose_name = "Agence"
        verbose_name_plural = "Agences"
        ordering = ['nom']
        indexes = [
            models.Index(fields=['code']),
            models.Index(fields=['ville']),
            models.Index(fields=['est_active']),
        ]

    def __str__(self):
        return f"{self.nom} ({self.code})"

    @property
    def adresse_complete(self):
        """Obtenir l'adresse complète formatée"""
        parties = [self.adresse, self.ville]
        if self.code_postal:
            parties.append(self.code_postal)
        if self.region:
            parties.append(self.region)
        return ', '.join(parties)

    @property
    def total_employes(self):
        """Obtenir le nombre total d'employés dans cette agence"""
        return self.employes.filter(type_utilisateur='CLIENT').count()

    @property
    def employes_actifs(self):
        """Obtenir le nombre d'employés actifs dans cette agence"""
        return self.employes.filter(type_utilisateur='CLIENT', est_actif=True).count()

    @property
    def a_capacite(self):
        """Vérifier si l'agence peut accepter plus d'employés"""
        if self.capacite_max_employes is None:
            return True
        return self.total_employes < self.capacite_max_employes

    def get_niveau_hierarchie(self):
        """Obtenir le niveau hiérarchique de cette agence"""
        niveau = 0
        courant = self
        while courant.agence_parente:
            niveau += 1
            courant = courant.agence_parente
        return niveau

    def get_toutes_sous_agences(self):
        """Obtenir toutes les sous-agences récursivement"""
        sous_agences = list(self.sous_agences.all())
        for sous in self.sous_agences.all():
            sous_agences.extend(sous.get_toutes_sous_agences())
        return sous_agences


class ProfilUtilisateur(models.Model):
    """Profil étendu de l'utilisateur"""

    utilisateur = models.OneToOneField(
        Utilisateur,
        on_delete=models.CASCADE,
        related_name='profil'
    )

    # Préférences
    notification_email = models.BooleanField("Notifications email", default=True)
    notification_sms = models.BooleanField("Notifications SMS", default=False)
    langue = models.CharField("Langue", max_length=10, default='fr')

    # Contact d'urgence
    contact_urgence_nom = models.CharField("Contact d'urgence", max_length=200, blank=True)
    contact_urgence_telephone = models.CharField("Téléphone d'urgence", max_length=17, blank=True)

    # Informations supplémentaires
    notes = models.TextField("Notes", blank=True)

    # Dates
    date_creation = models.DateTimeField("Créé le", auto_now_add=True)
    date_modification = models.DateTimeField("Modifié le", auto_now=True)

    class Meta:
        verbose_name = "Profil utilisateur"
        verbose_name_plural = "Profils utilisateurs"

    def __str__(self):
        return f"Profil de {self.utilisateur.get_full_name()}"