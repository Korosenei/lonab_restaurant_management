"""
Vues pour l'application transactions
"""
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.db.models import Q, Sum, Count
from django.core.paginator import Paginator
from django.utils import timezone
from django.conf import settings
from dateutil.relativedelta import relativedelta
from .models import TransactionTicket, LogConsommation

from apps.accounts.models import Utilisateur, Agence
from apps.settings.models import ParametresSysteme


def _debut_fin_mois(date=None):
    d = date or timezone.now().date()
    debut = d.replace(day=1)
    fin   = debut + relativedelta(months=1) - relativedelta(days=1)
    return debut, fin


def _get_params():
    """Charge les paramètres depuis la DB, fallback settings.py."""
    try:
        p = ParametresSysteme.charger()
        return {
            'prix_ticket': int(p.prix_ticket),
            'subvention':  int(p.subvention_ticket),
            'min_tickets': p.tickets_min_par_transaction,
            'max_tickets': p.tickets_max_par_transaction,
            'max_mensuel': p.transactions_max_par_mois,
        }
    except Exception:
        return {
            'prix_ticket': getattr(settings, 'TICKET_PRICE', 500),
            'subvention':  getattr(settings, 'TICKET_SUBSIDY', 1500),
            'min_tickets': getattr(settings, 'MIN_TICKETS_PER_TRANSACTION', 1),
            'max_tickets': getattr(settings, 'MAX_TICKETS_PER_TRANSACTION', 20),
            'max_mensuel': getattr(settings, 'MAX_TRANSACTIONS_PER_MONTH', 1),
        }


# ═══════════════════════════════════════════════════════════════
# ADMIN
# ═══════════════════════════════════════════════════════════════
@login_required
def admin_transactions(request):
    if not request.user.est_admin:
        return redirect('accounts:dashboard')

    qs = TransactionTicket.objects.select_related('client', 'caissier', 'agence')

    if search := request.GET.get('search'):
        qs = qs.filter(
            Q(numero_transaction__icontains=search) |
            Q(client__prenom__icontains=search) |
            Q(client__nom__icontains=search) |
            Q(client__matricule__icontains=search)
        )
    if statut := request.GET.get('statut'):
        qs = qs.filter(statut=statut)
    if type_t := request.GET.get('type'):
        qs = qs.filter(type_transaction=type_t)
    if agence_id := request.GET.get('agence'):
        qs = qs.filter(agence_id=agence_id)
    if mois := request.GET.get('mois'):
        try:
            annee, m = mois.split('-')
            qs = qs.filter(date_transaction__year=annee, date_transaction__month=m)
        except ValueError:
            pass

    # Filtres période (date_debut / date_fin)
    if date_debut := request.GET.get('date_debut'):
        try:
            from datetime import date as dt
            y, m, d = date_debut.split('-')
            qs = qs.filter(date_transaction__date__gte=dt(int(y), int(m), int(d)))
        except Exception:
            pass
    if date_fin := request.GET.get('date_fin'):
        try:
            from datetime import date as dt
            y, m, d = date_fin.split('-')
            qs = qs.filter(date_transaction__date__lte=dt(int(y), int(m), int(d)))
        except Exception:
            pass

    totaux = qs.aggregate(
        total_montant=Sum('montant_total'),
        total_tickets=Sum('nombre_tickets'),
        nb_transactions=Count('id'),
    )

    paginator = Paginator(qs.order_by('-date_transaction'), 10)
    page_obj  = paginator.get_page(request.GET.get('page', 1))

    from apps.accounts.models import Agence
    return render(request, 'transactions/admin_transactions.html', {
        'transactions': page_obj,
        'page_obj':     page_obj,
        'totaux':       totaux,
        'agences':      Agence.objects.filter(est_active=True).order_by('nom'),
        'statuts':      TransactionTicket.STATUT_CHOICES,
        'types':        TransactionTicket.TYPE_TRANSACTION_CHOICES,
    })

@login_required
def transaction_detail(request, pk):
    t = get_object_or_404(TransactionTicket, pk=pk)
    if not (request.user.est_admin or t.caissier == request.user or t.client == request.user):
        return redirect('accounts:dashboard')
    tickets = t.tickets_genere.all().order_by('numero_ticket')
    return render(request, 'transactions/transaction_detail.html', {
        'transaction': t,
        'tickets': tickets,
        'peut_rembourser': (
            request.user.est_admin and
            t.statut == 'TERMINEE' and
            not tickets.filter(statut='CONSOMME').exists()
        ),
    })

@login_required
def admin_stats(request):
    if not request.user.est_admin:
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
@require_http_methods(["POST"])
def caissier_confirmer_vente(request):
    """Crée une transaction + génère les tickets."""
    if not (request.user.est_caissier or request.user.est_admin):
        return JsonResponse({'error': 'Permission refusée'}, status=403)
    try:
        from apps.accounts.models import Utilisateur
        params = _get_params()

        client     = get_object_or_404(Utilisateur, pk=request.POST.get('client_id'))
        nb_tickets = int(request.POST.get('nombre_tickets', 0))

        if nb_tickets < params['min_tickets'] or nb_tickets > params['max_tickets']:
            return JsonResponse(
                {'error': f"Nombre de tickets entre {params['min_tickets']} et {params['max_tickets']}"},
                status=400
            )

        debut_mois, fin_mois = _debut_fin_mois()
        nb_ce_mois = TransactionTicket.objects.filter(
            client=client, type_transaction='ACHAT', statut='TERMINEE',
            date_transaction__date__gte=debut_mois,
        ).count()

        if nb_ce_mois >= params['max_mensuel']:
            return JsonResponse(
                {'error': f"Le client a déjà atteint sa limite de {params['max_mensuel']} transaction(s) ce mois"},
                status=400
            )

        transaction = TransactionTicket.objects.create(
            client=client,
            caissier=request.user,
            agence=request.user.agence,
            type_transaction='ACHAT',
            nombre_tickets=nb_tickets,
            premier_ticket='',
            dernier_ticket='',
            valide_de=debut_mois,
            valide_jusqu_a=fin_mois,
            prix_unitaire=params['prix_ticket'],
            subvention_par_ticket=params['subvention'],
            montant_total=nb_tickets * params['prix_ticket'],
            subvention_totale=nb_tickets * params['subvention'],
            mode_paiement='ESPECES',
            notes=request.POST.get('notes', ''),
            statut='TERMINEE',
        )
        transaction.generer_tickets()

        return JsonResponse({
            'success':        True,
            'message':        f"{nb_tickets} ticket(s) créé(s) pour {client.get_full_name()}",
            'transaction_id': transaction.id,
            'numero':         transaction.numero_transaction,
            'premier_ticket': transaction.premier_ticket,
            'dernier_ticket': transaction.dernier_ticket,
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

@login_required
def caissier_historique(request):
    if not (request.user.est_caissier or request.user.est_admin):
        return redirect('accounts:dashboard')
    qs = TransactionTicket.objects.filter(caissier=request.user).select_related('client', 'agence')
    if search := request.GET.get('search'):
        qs = qs.filter(
            Q(numero_transaction__icontains=search) |
            Q(client__prenom__icontains=search) | Q(client__nom__icontains=search)
        )
    if statut := request.GET.get('statut'):
        qs = qs.filter(statut=statut)
    if mois := request.GET.get('mois'):
        try:
            annee, m = mois.split('-')
            qs = qs.filter(date_transaction__year=annee, date_transaction__month=m)
        except ValueError:
            pass
    paginator = Paginator(qs.order_by('-date_transaction'), 10)
    page_obj  = paginator.get_page(request.GET.get('page', 1))
    return render(request, 'transactions/caissier_historique.html', {
        'transactions': page_obj,
        'page_obj':     page_obj,
        'statuts':      TransactionTicket.STATUT_CHOICES,
    })

@login_required
def caissier_clients(request):
    if not (request.user.est_caissier or request.user.est_admin):
        return redirect('accounts:dashboard')
    from apps.accounts.models import Utilisateur
    # Clients de la même agence que le caissier uniquement
    qs = Utilisateur.objects.filter(
        type_utilisateur='CLIENT', est_actif=True,
        agence=request.user.agence,
    ).select_related('agence', 'direction')
    if search := request.GET.get('search'):
        qs = qs.filter(
            Q(prenom__icontains=search) | Q(nom__icontains=search) |
            Q(matricule__icontains=search) | Q(email__icontains=search)
        )
    from django.core.paginator import Paginator
    paginator = Paginator(qs.order_by('nom', 'prenom'), 10)
    page_obj  = paginator.get_page(request.GET.get('page', 1))
    return render(request, 'transactions/caissier_clients.html', {
        'clients':  page_obj,
        'page_obj': page_obj,
        'agence':   request.user.agence,
    })

@login_required
def caissier_client_detail(request, pk):
    if not (request.user.est_caissier or request.user.est_admin):
        return redirect('accounts:dashboard')
    from apps.accounts.models import Utilisateur
    params = _get_params()
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
        'client':               client,
        'tickets_valides':      tickets_valides,
        'nb_tickets_valides':   tickets_valides.count(),
        'transactions':         transactions,
        'nb_transactions_mois': nb_transactions_mois,
        'peut_acheter':         nb_transactions_mois < params['max_mensuel'],
        'debut_mois':           debut_mois,
        'fin_mois':             fin_mois,
    })

@login_required
@require_http_methods(["POST"])
def rembourser_transaction(request, pk):
    if not request.user.est_admin:
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
        'transactions':           transactions,
        'tickets_valides':        tickets_valides,
        'tickets_consommes_mois': tickets_consommes_mois,
        'aujourd_hui':            aujourd_hui,
    })

