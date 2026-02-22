"""
Administration — App Tickets
"""
from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from .models import Ticket, CodeQR


# ================================================================
# TICKET ADMIN
# ================================================================

@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):

    list_display = (
        'numero_ticket', 'proprietaire_display', 'statut_display',
        'validite_display', 'restaurant_col', 'prix_display', 'date_creation',
    )
    list_filter = (
        'statut',
        ('valide_de', admin.DateFieldListFilter),
        ('date_consommation', admin.DateFieldListFilter),
        'proprietaire__agence',
        'restaurant_consommateur',
    )
    search_fields = (
        'numero_ticket',
        'proprietaire__prenom', 'proprietaire__nom',
        'proprietaire__matricule', 'proprietaire__email',
    )
    readonly_fields = (
        'numero_ticket', 'date_creation', 'date_modification',
        'proprietaire', 'transaction', 'prix_paye', 'montant_subventionne',
    )
    ordering = ('-date_creation',)
    date_hierarchy = 'date_creation'
    list_per_page = 50

    fieldsets = (
        ('🎫 Ticket', {
            'fields': ('numero_ticket', 'statut'),
        }),
        ('👤 Propriétaire', {
            'fields': ('proprietaire', 'transaction'),
        }),
        ('📅 Validité', {
            'fields': ('valide_de', 'valide_jusqua'),
        }),
        ('🍽️ Consommation', {
            'fields': ('date_consommation', 'restaurant_consommateur', 'valide_par'),
        }),
        ('💰 Financier', {
            'fields': ('prix_paye', 'montant_subventionne'),
        }),
        ('🕐 Horodatage', {
            'fields': ('date_creation', 'date_modification'),
            'classes': ('collapse',),
        }),
    )

    actions = [
        'marquer_disponibles', 'marquer_annules', 'marquer_expires', 'exporter_csv',
    ]

    # ── Colonnes ────────────────────────────────────────────────

    @admin.display(description='Propriétaire', ordering='proprietaire__nom')
    def proprietaire_display(self, obj):
        return format_html(
            '<strong>{}</strong><br><small style="color:#6c757d;">{}</small>',
            obj.proprietaire.get_full_name(),
            obj.proprietaire.matricule or obj.proprietaire.email,
        )

    @admin.display(description='Statut', ordering='statut')
    def statut_display(self, obj):
        cfg = {
            'DISPONIBLE': ('#28a745', '#fff', '✓ Disponible'),
            'CONSOMME':   ('#17a2b8', '#fff', '🍴 Consommé'),
            'EXPIRE':     ('#ffc107', '#000', '⏰ Expiré'),
            'ANNULE':     ('#dc3545', '#fff', '✗ Annulé'),
        }
        bg, fg, label = cfg.get(obj.statut, ('#6c757d', '#fff', obj.statut))
        return format_html(
            '<span style="background:{};color:{};padding:2px 9px;border-radius:10px;font-size:11px;font-weight:600;">{}</span>',
            bg, fg, label,
        )

    @admin.display(description='Validité')
    def validite_display(self, obj):
        today = timezone.now().date()
        if obj.valide_jusqua and today > obj.valide_jusqua and obj.statut == 'DISPONIBLE':
            color = '#dc3545'
        else:
            color = '#6c757d'
        return format_html(
            '<small style="color:{};">{} → {}</small>',
            color,
            obj.valide_de.strftime('%d/%m/%Y') if obj.valide_de else '—',
            obj.valide_jusqua.strftime('%d/%m/%Y') if obj.valide_jusqua else '—',
        )

    @admin.display(description='Consommé chez')
    def restaurant_col(self, obj):
        if obj.restaurant_consommateur:
            return format_html(
                '<span style="color:#28a745;"><i>🏪</i> {}</span>',
                obj.restaurant_consommateur.nom,
            )
        return '—'

    @admin.display(description='Prix payé', ordering='prix_paye')
    def prix_display(self, obj):
        return format_html('<small>{:,.0f} FCFA</small>', obj.prix_paye or 0)

    # ── Actions ────────────────────────────────────────────────

    @admin.action(description='✓ Marquer comme disponibles')
    def marquer_disponibles(self, request, queryset):
        count = queryset.exclude(statut='CONSOMME').update(statut='DISPONIBLE')
        self.message_user(request, f'{count} ticket(s) marqué(s) comme disponible(s).')

    @admin.action(description='✗ Marquer comme annulés')
    def marquer_annules(self, request, queryset):
        count = queryset.exclude(statut='CONSOMME').update(statut='ANNULE')
        self.message_user(request, f'{count} ticket(s) annulé(s).')

    @admin.action(description='⏰ Marquer comme expirés')
    def marquer_expires(self, request, queryset):
        count = queryset.filter(statut='DISPONIBLE').update(statut='EXPIRE')
        self.message_user(request, f'{count} ticket(s) marqué(s) comme expirés.')

    @admin.action(description='📥 Exporter en CSV')
    def exporter_csv(self, request, queryset):
        import csv
        from django.http import HttpResponse
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = 'attachment; filename="tickets.csv"'
        response.write('\ufeff')
        writer = csv.writer(response)
        writer.writerow([
            'N° Ticket', 'Propriétaire', 'Matricule',
            'Statut', 'Valide du', 'Valide au',
            'Prix payé', 'Restaurant', 'Date consommation',
        ])
        for t in queryset.select_related('proprietaire', 'restaurant_consommateur'):
            writer.writerow([
                t.numero_ticket,
                t.proprietaire.get_full_name(),
                t.proprietaire.matricule or '',
                t.statut,
                t.valide_de.strftime('%d/%m/%Y') if t.valide_de else '',
                t.valide_jusqua.strftime('%d/%m/%Y') if t.valide_jusqua else '',
                t.prix_paye,
                t.restaurant_consommateur.nom if t.restaurant_consommateur else '',
                t.date_consommation.strftime('%d/%m/%Y %H:%M') if t.date_consommation else '',
            ])
        return response


# ================================================================
# CODE QR ADMIN
# ================================================================

@admin.register(CodeQR)
class CodeQRAdmin(admin.ModelAdmin):

    list_display = (
        'code_display', 'utilisateur_display',
        'validite_col', 'expire_display',
        'statut_qr_display', 'restaurant_col', 'date_creation',
    )
    list_filter = (
        'est_valide', 'est_utilise',
        ('expire_le', admin.DateFieldListFilter),
        ('utilise_le', admin.DateFieldListFilter),
        'utilise_par_restaurant',
    )
    search_fields = (
        'code',
        'utilisateur__prenom', 'utilisateur__nom',
        'utilisateur__email', 'utilisateur__matricule',
    )
    readonly_fields = (
        'code', 'image_qr', 'date_creation',
        'utilisateur', 'expire_le',
        'utilise_le', 'utilise_par_restaurant',
    )
    ordering = ('-date_creation',)
    date_hierarchy = 'date_creation'
    list_per_page = 40

    fieldsets = (
        ('📱 Code QR', {
            'fields': ('code', 'image_qr', 'donnees_tickets'),
        }),
        ('👤 Utilisateur', {
            'fields': ('utilisateur',),
        }),
        ('✅ Validité', {
            'fields': ('est_valide', 'expire_le'),
        }),
        ('🔍 Utilisation', {
            'fields': ('est_utilise', 'utilise_le', 'utilise_par_restaurant'),
        }),
        ('🕐 Horodatage', {
            'fields': ('date_creation',),
        }),
    )

    actions = ['invalider_codes', 'exporter_csv']

    # ── Colonnes ────────────────────────────────────────────────

    @admin.display(description='Code QR')
    def code_display(self, obj):
        return format_html('<code style="font-size:11px;">{}</code>', obj.code[:16] + '…')

    @admin.display(description='Utilisateur', ordering='utilisateur__nom')
    def utilisateur_display(self, obj):
        return format_html(
            '<strong>{}</strong><br><small style="color:#6c757d;">{}</small>',
            obj.utilisateur.get_full_name(),
            obj.utilisateur.matricule or obj.utilisateur.email,
        )

    @admin.display(description='Statut')
    def statut_qr_display(self, obj):
        now = timezone.now()
        if obj.est_utilise:
            label, bg, fg = 'Utilisé', '#17a2b8', '#fff'
        elif not obj.est_valide:
            label, bg, fg = 'Invalidé', '#dc3545', '#fff'
        elif obj.expire_le and now > obj.expire_le:
            label, bg, fg = 'Expiré', '#ffc107', '#000'
        else:
            label, bg, fg = 'Valide', '#28a745', '#fff'
        return format_html(
            '<span style="background:{};color:{};padding:2px 9px;border-radius:10px;font-size:11px;font-weight:600;">{}</span>',
            bg, fg, label,
        )

    @admin.display(description='Validité')
    def validite_col(self, obj):
        if not obj.est_valide:
            return format_html('<span style="color:#dc3545;">Invalide</span>')
        return format_html('<span style="color:#28a745;">Valide</span>')

    @admin.display(description='Expire le', ordering='expire_le')
    def expire_display(self, obj):
        if not obj.expire_le:
            return '—'
        color = '#dc3545' if timezone.now() > obj.expire_le else '#6c757d'
        return format_html(
            '<small style="color:{};">{}</small>',
            color,
            obj.expire_le.strftime('%d/%m/%Y %H:%M'),
        )

    @admin.display(description='Scanné par')
    def restaurant_col(self, obj):
        if obj.utilise_par_restaurant:
            return format_html('🏪 {}', obj.utilise_par_restaurant.nom)
        return '—'

    # ── Actions ────────────────────────────────────────────────

    @admin.action(description='🚫 Invalider les codes sélectionnés')
    def invalider_codes(self, request, queryset):
        count = queryset.filter(est_valide=True, est_utilise=False).update(est_valide=False)
        self.message_user(request, f'{count} code(s) QR invalidé(s).')

    @admin.action(description='📥 Exporter en CSV')
    def exporter_csv(self, request, queryset):
        import csv
        from django.http import HttpResponse
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = 'attachment; filename="codes_qr.csv"'
        response.write('\ufeff')
        writer = csv.writer(response)
        writer.writerow([
            'Code', 'Utilisateur', 'Valide', 'Utilisé',
            'Expire le', 'Utilisé le', 'Restaurant', 'Créé le',
        ])
        for qr in queryset.select_related('utilisateur', 'utilise_par_restaurant'):
            writer.writerow([
                qr.code,
                qr.utilisateur.get_full_name(),
                'Oui' if qr.est_valide else 'Non',
                'Oui' if qr.est_utilise else 'Non',
                qr.expire_le.strftime('%d/%m/%Y %H:%M') if qr.expire_le else '',
                qr.utilise_le.strftime('%d/%m/%Y %H:%M') if qr.utilise_le else '',
                qr.utilise_par_restaurant.nom if qr.utilise_par_restaurant else '',
                qr.date_creation.strftime('%d/%m/%Y %H:%M') if qr.date_creation else '',
            ])
        return response
