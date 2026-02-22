"""
Administration — App Transactions
"""
from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from .models import TransactionTicket
from apps.tickets.models import Ticket


# ================================================================
# INLINE
# ================================================================

class TicketInline(admin.TabularInline):
    model = Ticket
    extra = 0
    can_delete = False
    show_change_link = True
    readonly_fields = ('numero_ticket', 'statut', 'valide_de', 'valide_jusqua')
    fields = ('numero_ticket', 'statut', 'valide_de', 'valide_jusqua')
    verbose_name = "Ticket généré"
    verbose_name_plural = "Tickets générés"

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


# ================================================================
# TRANSACTION TICKET ADMIN
# ================================================================

@admin.register(TransactionTicket)
class TransactionTicketAdmin(admin.ModelAdmin):

    inlines = [TicketInline]

    list_display = (
        'numero_transaction', 'client_display', 'caissier_display',
        'nb_tickets_col', 'montant_display', 'mode_paiement',
        'statut_display', 'date_transaction_col',
    )
    list_filter = (
        'statut', 'mode_paiement', 'type_transaction',
        ('date_transaction', admin.DateFieldListFilter),
        'caissier__agence',
    )
    search_fields = (
        'numero_transaction',
        'client__prenom', 'client__nom', 'client__email', 'client__matricule',
        'caissier__prenom', 'caissier__nom',
    )

    # Champs en lecture seule - exclure les méthodes d'affichage
    readonly_fields = (
        'numero_transaction', 'date_transaction', 'date_modification',
        'montant_total', 'subvention_totale',
    )

    ordering = ('-date_transaction',)
    date_hierarchy = 'date_transaction'
    list_per_page = 40

    # Utiliser seulement fieldsets
    fieldsets = (
        ('🔖 Référence', {
            'fields': ('type_transaction', 'statut'),
        }),
        ('👥 Participants', {
            'fields': ('client', 'caissier', 'agence'),
        }),
        ('💰 Financier', {
            'fields': (
                'nombre_tickets', 'prix_unitaire', 'subvention_par_ticket',
                'montant_total', 'subvention_totale',
                'mode_paiement', 'reference_paiement',
            ),
        }),
        ('📅 Période de validité', {
            'fields': ('valide_de', 'valide_jusqu_a'),
        }),
        ('📝 Notes', {
            'fields': ('notes',),
            'classes': ('collapse',),
        }),
    )

    actions = ['marquer_terminees', 'marquer_echouees', 'exporter_csv']

    # ── Colonnes personnalisées ─────────────────────────────────

    @admin.display(description='Client', ordering='client__nom')
    def client_display(self, obj):
        if not obj.client:
            return '—'
        return format_html(
            '<strong>{}</strong><br><small style="color:#6c757d;">{}</small>',
            obj.client.get_full_name(),
            obj.client.matricule or obj.client.email,
        )

    @admin.display(description='Caissier', ordering='caissier__nom')
    def caissier_display(self, obj):
        if not obj.caissier:
            return '—'
        return format_html(
            '{}<br><small style="color:#6c757d;">{}</small>',
            obj.caissier.get_full_name(),
            obj.caissier.agence.nom if obj.caissier.agence else '—',
        )

    @admin.display(description='Tickets', ordering='nombre_tickets')
    def nb_tickets_col(self, obj):
        return format_html(
            '<span style="font-weight:700;color:#28a745;">{}</span>',
            obj.nombre_tickets,
        )

    @admin.display(description='Montant payé')
    def montant_display(self, obj):
        montant_paye = float(obj.montant_paye)
        return format_html(
            '<strong>{:,.0f} FCFA</strong>',
            montant_paye,
        )

    @admin.display(description='Statut', ordering='statut')
    def statut_display(self, obj):
        colors = {
            'EN_ATTENTE': ('#ffc107', '#000'),
            'TERMINEE':   ('#28a745', '#fff'),
            'ECHOUEE':    ('#dc3545', '#fff'),
            'REMBOURSE':  ('#6f42c1', '#fff'),
        }
        bg, fg = colors.get(obj.statut, ('#6c757d', '#fff'))
        return format_html(
            '<span style="background:{};color:{};padding:2px 8px;border-radius:10px;font-size:11px;font-weight:600;">{}</span>',
            bg, fg, obj.get_statut_display(),
        )

    @admin.display(description='Date', ordering='date_transaction')
    def date_transaction_col(self, obj):
        if obj.date_transaction:
            return format_html(
                '<small>{}</small>',
                obj.date_transaction.strftime('%d/%m/%Y %H:%M'),
            )
        return '—'

    # ── Actions ────────────────────────────────────────────────

    @admin.action(description='✅ Marquer comme terminées')
    def marquer_terminees(self, request, queryset):
        count = 0
        for transaction in queryset.filter(statut='EN_ATTENTE'):
            try:
                transaction.completer()
                count += 1
            except Exception as e:
                self.message_user(request, f"Erreur pour {transaction}: {str(e)}", level='ERROR')
        self.message_user(request, f'{count} transaction(s) marquée(s) comme terminée(s).')

    @admin.action(description='❌ Marquer comme échouées')
    def marquer_echouees(self, request, queryset):
        count = queryset.filter(statut='EN_ATTENTE').update(statut='ECHOUEE')
        self.message_user(request, f'{count} transaction(s) marquée(s) comme échouée(s).')

    @admin.action(description='📥 Exporter en CSV')
    def exporter_csv(self, request, queryset):
        import csv
        from django.http import HttpResponse
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = 'attachment; filename="transactions.csv"'
        response.write('\ufeff')
        writer = csv.writer(response)
        writer.writerow(['Numéro', 'Client', 'Matricule', 'Caissier', 'Tickets', 'Montant total', 'Subvention', 'Montant payé', 'Mode', 'Statut', 'Date'])
        for t in queryset.select_related('client', 'caissier'):
            writer.writerow([
                t.numero_transaction,
                t.client.get_full_name() if t.client else '',
                t.client.matricule if t.client else '',
                t.caissier.get_full_name() if t.caissier else '',
                t.nombre_tickets,
                f"{float(t.montant_total):,.0f}" if t.montant_total else '0',
                f"{float(t.subvention_totale):,.0f}" if t.subvention_totale else '0',
                f"{float(t.montant_paye):,.0f}",
                t.get_mode_paiement_display(),
                t.get_statut_display(),
                t.date_transaction.strftime('%d/%m/%Y %H:%M') if t.date_transaction else '',
            ])
        return response

    # ── Override get_queryset ───────────────────

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'client', 'caissier', 'caissier__agence', 'agence'
        )

    # ── Personnalisation du formulaire ─────────────────────────

    def get_readonly_fields(self, request, obj=None):
        """Ajuster les champs en lecture seule selon le contexte"""
        if obj is None:  # Mode ajout
            return ['numero_transaction', 'montant_total', 'subvention_totale']
        else:  # Mode édition
            return self.readonly_fields + ['date_creation', 'date_transaction', 'date_modification']

    def get_fieldsets(self, request, obj=None):
        """Personnaliser les fieldsets selon le contexte"""
        fieldsets = super().get_fieldsets(request, obj)

        if obj:  # En mode édition, ajouter les champs supplémentaires
            # Ajouter le numéro de transaction
            fieldsets = list(fieldsets)
            fieldsets[0] = ('🔖 Référence', {
                'fields': ('numero_transaction', 'type_transaction', 'statut'),
            })
            # Ajouter les dates
            fieldsets.append(('📅 Dates', {
                'fields': ('date_transaction', 'date_creation', 'date_modification'),
                'classes': ('collapse',),
            }))
            # Ajouter les numéros de tickets
            fieldsets.append(('📋 Tickets', {
                'fields': ('premier_ticket', 'dernier_ticket'),
                'classes': ('collapse',),
            }))

        return fieldsets
