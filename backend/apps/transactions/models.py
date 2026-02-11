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
    nombre_tickets = models.IntegerField('Nombre de tickets')
    premier_ticket = models.CharField('Numéro du premier ticket', max_length=50)
    dernier_ticket = models.CharField('Numéro du dernier ticket', max_length=50)

    # Période de validité
    valide_de = models.DateField('Valide à partir du')
    valide_jusqu_a = models.DateField('Valide jusqu\'au')

    # Montants
    prix_unitaire = models.DecimalField('Prix unitaire', max_digits=10, decimal_places=2)
    subvention_par_ticket = models.DecimalField('Subvention par ticket', max_digits=10, decimal_places=2)
    montant_total = models.DecimalField('Montant total', max_digits=10, decimal_places=2)
    subvention_totale = models.DecimalField('Subvention totale', max_digits=10, decimal_places=2)

    # Paiement
    mode_paiement = models.CharField('Mode de paiement', max_length=20, choices=MODE_PAIEMENT_CHOICES)
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

    def save(self, *args, **kwargs):
        """Générer le numéro de transaction et calculer les montants"""
        if not self.numero_transaction:
            maintenant = timezone.now()
            self.numero_transaction = f"{maintenant.strftime('%Y%m%d-%H%M%S')}-{self.client.id}"

        self.montant_total = self.nombre_tickets * self.prix_unitaire
        self.subvention_totale = self.nombre_tickets * self.subvention_par_ticket

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
        if self.generated_tickets.exists():
            raise ValidationError('Tickets déjà générés pour cette transaction')

        annee_mois = self.date_transaction.strftime('%Y%m')
        dernier_ticket = Ticket.objects.filter(ticket_number__startswith=annee_mois).order_by('-ticket_number').first()

        start_sequence = int(dernier_ticket.ticket_number.split('-')[1]) + 1 if dernier_ticket else 1

        tickets = []
        for i in range(self.nombre_tickets):
            numero_ticket = f"{annee_mois}-{str(start_sequence + i).zfill(5)}"
            tickets.append(Ticket(
                ticket_number=numero_ticket,
                owner=self.client,
                transaction=self,
                valid_from=self.valide_de,
                valid_until=self.valide_jusqu_a,
                price_paid=self.prix_unitaire,
                subsidy_amount=self.subvention_par_ticket
            ))

        Ticket.objects.bulk_create(tickets)
        self.premier_ticket = tickets[0].ticket_number
        self.dernier_ticket = tickets[-1].ticket_number
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
        if self.generated_tickets.filter(status='CONSUMED').exists():
            raise ValidationError('Impossible de rembourser: certains tickets ont déjà été consommés')

        self.generated_tickets.update(status='CANCELLED')
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
        return f"Consommation {self.ticket.ticket_number} - {self.date_consommation}"
