"""
Vues pour l'application transactions
"""
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib import messages
from django.db.models import Q, Sum, Count
from django.utils import timezone
from django.conf import settings
from dateutil.relativedelta import relativedelta
from .models import TransactionTicket, LogConsommation


def _debut_fin_mois(date=None):
    d = date or timezone.now().date()
    debut = d.replace(day=1)
    fin   = debut + relativedelta(months=1) - relativedelta(days=1)
    return debut, fin


# ───────────────────────────────────────────────────────────────
# ADMIN
# ───────────────────────────────────────────────────────────────
@login_required
def admin_transactions_list(request):
    if not request.user.est_super_admin:
        return redirect('accounts:dashboard')
    qs = TransactionTicket.objects.select_related('client', 'caissier', 'agence')
    if search := request.GET.get('search'):
        qs = qs.filter(
            Q(numero_transaction__icontains=search) |
            Q(client__prenom__icontains=search) |
            Q(client__nom__icontains=search) |
            Q(client__matricule__icontains=search)
        )
    if statut := request.GET.get('statut'): qs = qs.filter(statut=statut)
    if type_t := request.GET.get('type'): qs = qs.filter(type_transaction=type_t)
    if mois := request.GET.get('mois'):
        annee, m = mois.split('-')
        qs = qs.filter(date_transaction__year=annee, date_transaction__month=m)
    totaux = qs.aggregate(
        total_montant=Sum('montant_total'),
        total_tickets=Sum('nombre_tickets'),
        nb_transactions=Count('id'),
    )
    return render(request, 'transactions/admin_transactions.html', {
        'transactions': qs.order_by('-date_transaction')[:200],
        'totaux': totaux,
        'statuts': TransactionTicket.STATUT_CHOICES,
        'types': TransactionTicket.TYPE_TRANSACTION_CHOICES,
    })

@login_required
def transaction_detail(request, pk):
    t = get_object_or_404(TransactionTicket, pk=pk)
    if not (request.user.est_super_admin or t.caissier == request.user or t.client == request.user):
        return redirect('accounts:dashboard')
    tickets = t.tickets_genere.all().order_by('numero_ticket')
    return render(request, 'transactions/transaction_detail.html', {
        'transaction': t,
        'tickets': tickets,
        'peut_rembourser': (
            request.user.est_super_admin and
            t.statut == 'TERMINEE' and
            not tickets.filter(statut='CONSOMME').exists()
        ),
    })

@login_required
def admin_stats(request):
    if not request.user.est_super_admin:
        return redirect('accounts:dashboard')
    aujourd_hui = timezone.now().date()
    debut_mois, fin_mois = _debut_fin_mois(aujourd_hui)
    debut_semaine = aujourd_hui - timezone.timedelta(days=aujourd_hui.weekday())
    stats = {
        'tickets_mois': TransactionTicket.objects.filter(
            statut='TERMINEE', date_transaction__date__gte=debut_mois,
        ).aggregate(t=Sum('nombre_tickets'))['t'] or 0,
        'ca_mois': TransactionTicket.objects.filter(
            statut='TERMINEE', date_transaction__date__gte=debut_mois,
        ).aggregate(s=Sum('montant_total'))['s'] or 0,
        'transactions_semaine': TransactionTicket.objects.filter(
            date_transaction__date__gte=debut_semaine).count(),
        'consommations_mois': LogConsommation.objects.filter(
            date_consommation__date__gte=debut_mois).count(),
    }
    ventes_jour = []
    for i in range(29, -1, -1):
        j = aujourd_hui - timezone.timedelta(days=i)
        nb = TransactionTicket.objects.filter(
            statut='TERMINEE', date_transaction__date=j
        ).aggregate(t=Sum('nombre_tickets'))['t'] or 0
        ventes_jour.append({'date': j.strftime('%d/%m'), 'tickets': nb})
    return render(request, 'transactions/admin_stats.html', {
        'stats': stats, 'ventes_jour': ventes_jour,
    })


# ═══════════════════════════════════════════════════════════════
# CAISSIER
# ═══════════════════════════════════════════════════════════════
@login_required
def caissier_dashboard(request):
    if not (request.user.est_caissier or request.user.est_super_admin):
        return redirect('accounts:dashboard')
    aujourd_hui = timezone.now().date()
    debut_mois, _ = _debut_fin_mois(aujourd_hui)
    mes_transactions = TransactionTicket.objects.filter(caissier=request.user)
    stats = {
        'aujourd_hui': mes_transactions.filter(date_transaction__date=aujourd_hui).count(),
        'tickets_mois': mes_transactions.filter(
            statut='TERMINEE', date_transaction__date__gte=debut_mois
        ).aggregate(t=Sum('nombre_tickets'))['t'] or 0,
        'ca_mois': mes_transactions.filter(
            statut='TERMINEE', date_transaction__date__gte=debut_mois
        ).aggregate(s=Sum('montant_total'))['s'] or 0,
        'en_attente': mes_transactions.filter(statut='EN_ATTENTE').count(),
    }
    recentes = mes_transactions.select_related('client').order_by('-date_transaction')[:8]
    return render(request, 'transactions/caissier_dashboard.html', {
        'stats': stats, 'recentes': recentes, 'aujourd_hui': aujourd_hui,
    })

@login_required
def caissier_tickets_list(request):
    """Liste de tous les tickets générés + modal de vente."""
    if not (request.user.est_caissier or request.user.est_super_admin):
        return redirect('accounts:dashboard')

    from apps.tickets.models import Ticket
    from apps.accounts.models import Utilisateur

    qs = Ticket.objects.select_related('proprietaire', 'transaction', 'restaurant_consommateur')

    if search := request.GET.get('search'):
        qs = qs.filter(
            Q(numero_ticket__icontains=search) |
            Q(proprietaire__prenom__icontains=search) |
            Q(proprietaire__nom__icontains=search) |
            Q(proprietaire__matricule__icontains=search)
        )
    if statut := request.GET.get('statut'):
        qs = qs.filter(statut=statut)
    if mois := request.GET.get('mois'):
        try:
            annee, m = mois.split('-')
            qs = qs.filter(valide_de__year=annee, valide_de__month=m)
        except ValueError:
            pass

    aujourd_hui = timezone.now().date()
    debut_mois, fin_mois = _debut_fin_mois(aujourd_hui)

    clients = Utilisateur.objects.filter(
        type_utilisateur='CLIENT', est_actif=True
    ).select_related('agence').order_by('nom', 'prenom')

    stats = {
        'total': qs.count(),
        'disponibles': qs.filter(statut='DISPONIBLE').count(),
        'consommes': qs.filter(statut='CONSOMME').count(),
        'expires': qs.filter(statut='EXPIRE').count(),
    }

    return render(request, 'transactions/caissier_tickets.html', {
        'tickets': qs.order_by('-date_creation')[:300],
        'stats': stats,
        'clients': clients,
        'debut_mois': debut_mois,
        'fin_mois': fin_mois,
        'prix_ticket': getattr(settings, 'TICKET_PRICE', 500),
        'subvention': getattr(settings, 'TICKET_SUBSIDY', 1500),
        'min_tickets': getattr(settings, 'MIN_TICKETS_PER_TRANSACTION', 1),
        'max_tickets': getattr(settings, 'MAX_TICKETS_PER_TRANSACTION', 22),
        'statuts': [('DISPONIBLE','Disponible'),('CONSOMME','Consommé'),
                    ('EXPIRE','Expiré'),('ANNULE','Annulé')],
    })

@login_required
@require_http_methods(["POST"])
def caissier_confirmer_vente(request):
    """Confirmer et créer une transaction + tickets (appelé depuis modal)."""
    if not (request.user.est_caissier or request.user.est_super_admin):
        return JsonResponse({'error': 'Permission refusée'}, status=403)
    try:
        from apps.accounts.models import Utilisateur
        client = get_object_or_404(Utilisateur, pk=request.POST.get('client_id'))
        nb_tickets = int(request.POST.get('nombre_tickets', 0))
        min_t = getattr(settings, 'MIN_TICKETS_PER_TRANSACTION', 1)
        max_t = getattr(settings, 'MAX_TICKETS_PER_TRANSACTION', 22)
        if nb_tickets < min_t or nb_tickets > max_t:
            return JsonResponse({'error': f'Nombre de tickets entre {min_t} et {max_t}'}, status=400)

        debut_mois, fin_mois = _debut_fin_mois()
        nb_ce_mois = TransactionTicket.objects.filter(
            client=client, type_transaction='ACHAT', statut='TERMINEE',
            date_transaction__date__gte=debut_mois,
        ).count()
        max_mensuel = getattr(settings, 'MAX_TRANSACTIONS_PER_MONTH', 1)
        if nb_ce_mois >= max_mensuel:
            return JsonResponse({
                'error': f'Le client a déjà atteint sa limite de {max_mensuel} transaction(s) ce mois'
            }, status=400)

        prix_unitaire = getattr(settings, 'TICKET_PRICE', 500)
        subvention    = getattr(settings, 'TICKET_SUBSIDY', 1500)

        transaction = TransactionTicket.objects.create(
            client=client, caissier=request.user, agence=request.user.agence,
            type_transaction='ACHAT', nombre_tickets=nb_tickets,
            premier_ticket='', dernier_ticket='',
            valide_de=debut_mois, valide_jusqu_a=fin_mois,
            prix_unitaire=prix_unitaire, subvention_par_ticket=subvention,
            montant_total=nb_tickets * prix_unitaire,
            subvention_totale=nb_tickets * subvention,
            mode_paiement='ESPECES',   # Fixé à Espèces
            notes=request.POST.get('notes', ''),
            statut='TERMINEE',
        )
        transaction.generer_tickets()

        return JsonResponse({
            'success': True,
            'message': f'{nb_tickets} ticket(s) créé(s) pour {client.get_full_name()}',
            'transaction_id': transaction.id,
            'numero': transaction.numero_transaction,
            'premier_ticket': transaction.premier_ticket,
            'dernier_ticket': transaction.dernier_ticket,
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

@login_required
def caissier_historique(request):
    if not (request.user.est_caissier or request.user.est_super_admin):
        return redirect('accounts:dashboard')
    qs = TransactionTicket.objects.filter(caissier=request.user).select_related('client', 'agence')
    if search := request.GET.get('search'):
        qs = qs.filter(
            Q(numero_transaction__icontains=search) |
            Q(client__prenom__icontains=search) | Q(client__nom__icontains=search)
        )
    if statut := request.GET.get('statut'): qs = qs.filter(statut=statut)
    if mois := request.GET.get('mois'):
        try:
            annee, m = mois.split('-')
            qs = qs.filter(date_transaction__year=annee, date_transaction__month=m)
        except ValueError:
            pass
    return render(request, 'transactions/caissier_historique.html', {
        'transactions': qs.order_by('-date_transaction'),
        'statuts': TransactionTicket.STATUT_CHOICES,
    })

@login_required
def caissier_clients(request):
    if not (request.user.est_caissier or request.user.est_super_admin):
        return redirect('accounts:dashboard')
    from apps.accounts.models import Utilisateur
    qs = Utilisateur.objects.filter(
        type_utilisateur='CLIENT', est_actif=True
    ).select_related('agence', 'direction')
    if search := request.GET.get('search'):
        qs = qs.filter(
            Q(prenom__icontains=search) | Q(nom__icontains=search) |
            Q(matricule__icontains=search) | Q(email__icontains=search)
        )
    return render(request, 'transactions/caissier_clients.html', {
        'clients': qs.order_by('nom', 'prenom'),
    })

@login_required
def caissier_client_detail(request, pk):
    if not (request.user.est_caissier or request.user.est_super_admin):
        return redirect('accounts:dashboard')
    from apps.accounts.models import Utilisateur
    client = get_object_or_404(Utilisateur, pk=pk, type_utilisateur='CLIENT')
    aujourd_hui = timezone.now().date()
    debut_mois, fin_mois = _debut_fin_mois(aujourd_hui)
    tickets_valides = client.tickets.filter(
        statut='DISPONIBLE', valide_de__lte=aujourd_hui, valide_jusqua__gte=aujourd_hui
    )
    transactions = TransactionTicket.objects.filter(client=client).order_by('-date_transaction')[:10]
    nb_transactions_mois = TransactionTicket.objects.filter(
        client=client, type_transaction='ACHAT', statut='TERMINEE',
        date_transaction__date__gte=debut_mois,
    ).count()
    return render(request, 'transactions/caissier_client_detail.html', {
        'client': client,
        'tickets_valides': tickets_valides,
        'nb_tickets_valides': tickets_valides.count(),
        'transactions': transactions,
        'nb_transactions_mois': nb_transactions_mois,
        'peut_acheter': nb_transactions_mois < getattr(settings, 'MAX_TRANSACTIONS_PER_MONTH', 1),
        'debut_mois': debut_mois, 'fin_mois': fin_mois,
    })

@login_required
@require_http_methods(["POST"])
def rembourser_transaction(request, pk):
    if not request.user.est_super_admin:
        return JsonResponse({'error': 'Permission refusée'}, status=403)
    t = get_object_or_404(TransactionTicket, pk=pk)
    try:
        t.rembourser()
        return JsonResponse({'success': True, 'message': f'Transaction {t.numero_transaction} remboursée'})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

# ═══════════════════════════════════════════════════════════════
# CLIENT
# ═══════════════════════════════════════════════════════════════
@login_required
def client_historique(request):
    if not request.user.est_client:
        return redirect('accounts:dashboard')
    aujourd_hui = timezone.now().date()
    debut_mois, _ = _debut_fin_mois(aujourd_hui)
    transactions = TransactionTicket.objects.filter(
        client=request.user
    ).order_by('-date_transaction')
    tickets_valides = request.user.tickets.filter(
        statut='DISPONIBLE', valide_de__lte=aujourd_hui, valide_jusqua__gte=aujourd_hui
    ).count()
    tickets_consommes_mois = request.user.tickets.filter(
        statut='CONSOMME', date_consommation__date__gte=debut_mois
    ).count()
    return render(request, 'transactions/client_historique.html', {
        'transactions': transactions,
        'tickets_valides': tickets_valides,
        'tickets_consommes_mois': tickets_consommes_mois,
        'aujourd_hui': aujourd_hui,
    })


