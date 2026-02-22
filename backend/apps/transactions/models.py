"""
Modèles pour la gestion des transactions de tickets et des consommations
"""
from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import datetime
from dateutil.relativedelta import relativedelta


class TransactionTicket(models.Model):
    """Transaction d'achat ou remboursement de tickets"""

    TYPE_TRANSACTION_CHOICES = [
        ('ACHAT', 'Achat'),
        ('REMBOURSEMENT', 'Remboursement'),
    ]

    MODE_PAIEMENT_CHOICES = [
        ('ESPECES', 'Espèces'),
        ('CARTE', 'Carte bancaire'),
        ('MOBILE', 'Mobile Money'),
        ('VIREMENT', 'Virement'),
    ]

    STATUT_CHOICES = [
        ('EN_ATTENTE', 'En attente'),
        ('TERMINEE', 'Complété'),
        ('ECHOUEE', 'Échoué'),
        ('REMBOURSE', 'Remboursé'),
    ]

    # Identification
    numero_transaction = models.CharField('Numéro de transaction', max_length=50, unique=True, db_index=True)
    type_transaction = models.CharField('Type', max_length=20, choices=TYPE_TRANSACTION_CHOICES, default='ACHAT')

    # Parties impliquées
    client = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='transactions_tickets',
        limit_choices_to={'type_utilisateur': 'CLIENT'}
    )

    caissier = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='transactions_traitees',
        limit_choices_to={'type_utilisateur': 'CASHIER'}
    )

    agence = models.ForeignKey(
        'accounts.Agence',
        on_delete=models.SET_NULL,
        null=True,
        related_name='transactions'
    )

    # Détails des tickets
    nombre_tickets = models.IntegerField('Nombre de tickets', default=1)
    premier_ticket = models.CharField('Numéro du premier ticket', max_length=50, blank=True)
    dernier_ticket = models.CharField('Numéro du dernier ticket', max_length=50, blank=True)

    # Période de validité
    valide_de = models.DateField('Valide à partir du', null=True, blank=True)
    valide_jusqu_a = models.DateField('Valide jusqu\'au', null=True, blank=True)

    # Montants
    prix_unitaire = models.DecimalField('Prix unitaire', max_digits=10, decimal_places=2, default=settings.TICKET_PRICE)
    subvention_par_ticket = models.DecimalField('Subvention par ticket', max_digits=10, decimal_places=2, default=settings.TICKET_SUBSIDY)
    montant_total = models.DecimalField('Montant total', max_digits=10, decimal_places=2, null=True, blank=True)
    subvention_totale = models.DecimalField('Subvention totale', max_digits=10, decimal_places=2, null=True, blank=True)

    # Paiement
    mode_paiement = models.CharField('Mode de paiement', max_length=20, choices=MODE_PAIEMENT_CHOICES, default='ESPECES')
    reference_paiement = models.CharField('Référence de paiement', max_length=100, blank=True)

    # Statut
    statut = models.CharField('Statut', max_length=20, choices=STATUT_CHOICES, default='EN_ATTENTE')
    notes = models.TextField('Notes', blank=True)

    date_transaction = models.DateTimeField('Date de transaction', default=timezone.now)
    date_creation = models.DateTimeField('Créé le', auto_now_add=True)
    date_modification = models.DateTimeField('Modifié le', auto_now=True)

    class Meta:
        verbose_name = 'Transaction de Tickets'
        verbose_name_plural = 'Transactions de Tickets'
        ordering = ['-date_transaction']
        indexes = [
            models.Index(fields=['numero_transaction']),
            models.Index(fields=['client', 'date_transaction']),
            models.Index(fields=['statut']),
        ]

    def __str__(self):
        return f"Transaction {self.numero_transaction} - {self.client.get_full_name()}"

    @property
    def montant_paye(self):
        """Montant effectivement payé par le client (total - subvention)"""
        if self.montant_total is not None and self.subvention_totale is not None:
            return self.montant_total - self.subvention_totale

        # Calculer à partir des valeurs unitaires si disponibles
        if self.nombre_tickets and self.prix_unitaire and self.subvention_par_ticket:
            total = self.nombre_tickets * self.prix_unitaire
            subv = self.nombre_tickets * self.subvention_par_ticket
            return total - subv

        return 0

    @property
    def montant_subventionne(self):
        """Alias pour subvention_totale"""
        if self.subvention_totale is not None:
            return self.subvention_totale

        if self.nombre_tickets and self.subvention_par_ticket:
            return self.nombre_tickets * self.subvention_par_ticket

        return 0

    def save(self, *args, **kwargs):
        """Générer le numéro de transaction et calculer les montants"""
        if not self.numero_transaction:
            maintenant = timezone.now()
            self.numero_transaction = f"{maintenant.strftime('%Y%m%d-%H%M%S')}-{self.client.id}"

        # Calculer les montants
        self.montant_total = self.nombre_tickets * self.prix_unitaire
        self.subvention_totale = self.nombre_tickets * self.subvention_par_ticket

        # Définir les dates de validité si non spécifiées
        if not self.valide_de:
            self.valide_de = timezone.now().date().replace(day=1)
        if not self.valide_jusqu_a:
            next_month = self.valide_de + relativedelta(months=1)
            self.valide_jusqu_a = next_month - relativedelta(days=1)

        super().save(*args, **kwargs)

    def clean(self):
        """Validation de la transaction"""
        if self.nombre_tickets < settings.MIN_TICKETS_PER_TRANSACTION:
            raise ValidationError(f'Nombre minimum de tickets : {settings.MIN_TICKETS_PER_TRANSACTION}')
        if self.nombre_tickets > settings.MAX_TICKETS_PER_TRANSACTION:
            raise ValidationError(f'Nombre maximum de tickets : {settings.MAX_TICKETS_PER_TRANSACTION}')

        if self.pk is None:
            debut_mois = timezone.now().date().replace(day=1)
            fin_mois = debut_mois + relativedelta(months=1)
            nb_transactions = TransactionTicket.objects.filter(
                client=self.client,
                type_transaction='ACHAT',
                statut='TERMINEE',
                date_transaction__gte=debut_mois,
                date_transaction__lt=fin_mois
            ).count()
            if nb_transactions >= settings.MAX_TRANSACTIONS_PER_MONTH:
                raise ValidationError(f'Limite de {settings.MAX_TRANSACTIONS_PER_MONTH} transaction(s)/mois atteinte')

    def generer_tickets(self):
        """Générer les tickets individuels"""
        from apps.tickets.models import Ticket

        if self.statut != 'TERMINEE':
            raise ValidationError('Les tickets ne peuvent être générés que pour les transactions complétées')
        if self.tickets_genere.exists():
            raise ValidationError('Tickets déjà générés pour cette transaction')

        annee_mois = self.date_transaction.strftime('%Y%m')
        dernier_ticket = Ticket.objects.filter(numero_ticket__startswith=annee_mois).order_by('-numero_ticket').first()

        start_sequence = int(dernier_ticket.numero_ticket.split('-')[1]) + 1 if dernier_ticket else 1

        tickets = []
        for i in range(self.nombre_tickets):
            numero_ticket = f"{annee_mois}-{str(start_sequence + i).zfill(5)}"
            tickets.append(Ticket(
                numero_ticket=numero_ticket,
                proprietaire=self.client,
                transaction=self,
                valide_de=self.valide_de,
                valide_jusqua=self.valide_jusqu_a,
                prix_paye=self.prix_unitaire,
                montant_subventionne=self.subvention_par_ticket
            ))

        Ticket.objects.bulk_create(tickets)
        self.premier_ticket = tickets[0].numero_ticket
        self.dernier_ticket = tickets[-1].numero_ticket
        self.save(update_fields=['premier_ticket', 'dernier_ticket'])
        return tickets

    def completer(self):
        """Compléter la transaction et générer les tickets"""
        self.statut = 'TERMINEE'
        self.save()
        return self.generer_tickets()

    def rembourser(self):
        """Rembourser la transaction"""
        if self.statut != 'TERMINEE':
            raise ValidationError('Seules les transactions complétées peuvent être remboursées')
        if self.tickets_genere.filter(statut='CONSOMME').exists():
            raise ValidationError('Impossible de rembourser: certains tickets ont déjà été consommés')

        self.tickets_genere.update(statut='ANNULE')
        self.statut = 'REMBOURSE'
        self.save()


class LogConsommation(models.Model):
    """Journal des consommations de tickets"""

    ticket = models.ForeignKey('tickets.Ticket', on_delete=models.CASCADE, related_name='logs_consommation')
    restaurant = models.ForeignKey('restaurants.Restaurant', on_delete=models.CASCADE, related_name='logs_consommation')
    client = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='logs_consommation', limit_choices_to={'type_utilisateur': 'CLIENT'})
    valide_par = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='consommations_validees', limit_choices_to={'type_utilisateur': 'RESTAURANT_MANAGER'})

    qr_code = models.ForeignKey('tickets.CodeQR', on_delete=models.SET_NULL, null=True, blank=True, related_name='logs_consommation')
    date_consommation = models.DateTimeField('Date de consommation', default=timezone.now)
    menu_consomme = models.ForeignKey('restaurants.Menu', on_delete=models.SET_NULL, null=True, blank=True, related_name='logs_consommation')
    agence = models.ForeignKey('accounts.Agence', on_delete=models.SET_NULL, null=True, related_name='logs_consommation')
    notes = models.TextField('Notes', blank=True)

    date_creation = models.DateTimeField('Créé le', auto_now_add=True)

    class Meta:
        verbose_name = 'Log de Consommation'
        verbose_name_plural = 'Logs de Consommation'
        ordering = ['-date_consommation']
        indexes = [
            models.Index(fields=['date_consommation']),
            models.Index(fields=['client', 'date_consommation']),
            models.Index(fields=['restaurant', 'date_consommation']),
        ]

    def __str__(self):
        return f"Consommation {self.ticket.numero_ticket} - {self.date_consommation}"


