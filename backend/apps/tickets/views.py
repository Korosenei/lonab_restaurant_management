"""
Vues pour l'application tickets
"""
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib import messages
from django.db.models import Q, Count, Sum
from django.core.paginator import Paginator
from dateutil.relativedelta import relativedelta
from django.utils import timezone
from django.conf import settings
from .models import Ticket, CodeQR

from apps.accounts.models import Utilisateur, Agence
from apps.settings.models import ParametresSysteme
from apps.transactions.models import TransactionTicket, LogConsommation


def _debut_fin_mois(date=None):
    from dateutil.relativedelta import relativedelta
    d = date or timezone.now().date()
    debut = d.replace(day=1)
    fin   = debut + relativedelta(months=1) - relativedelta(days=1)
    return debut, fin

def _get_params():
    """Charge les paramètres depuis la DB, fallback settings.py."""
    try:
        from apps.settings.models import ParametresSysteme
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


# ================================================================
# ADMIN
# ================================================================
@login_required
def admin_tickets(request):
    if not request.user.est_admin:
        return redirect('accounts:dashboard')

    qs = Ticket.objects.select_related(
        'proprietaire', 'proprietaire__agence', 'transaction', 'transaction__caissier',
        'restaurant_consommateur'
    )

    # ── Filtres ─────────────────────────────────────────────────
    q       = request.GET.get('search', '').strip()
    statut  = request.GET.get('statut', '').strip()
    agence  = request.GET.get('agence', '').strip()
    date_debut = request.GET.get('date_debut', '').strip()
    date_fin   = request.GET.get('date_fin', '').strip()
    mois    = request.GET.get('mois', '').strip()

    if q:
        qs = qs.filter(
            Q(numero_ticket__icontains=q) |
            Q(proprietaire__prenom__icontains=q) |
            Q(proprietaire__nom__icontains=q) |
            Q(proprietaire__matricule__icontains=q)
        )
    if statut:
        qs = qs.filter(statut=statut)
    if agence:
        qs = qs.filter(proprietaire__agence_id=agence)
    if mois:
        try:
            y, m = mois.split('-')
            qs = qs.filter(valide_de__year=y, valide_de__month=m)
        except ValueError:
            pass
    if date_debut:
        qs = qs.filter(date_creation__date__gte=date_debut)
    if date_fin:
        qs = qs.filter(date_creation__date__lte=date_fin)

    debut_mois, _ = _debut_fin_mois()
    totaux = {
        'total':          qs.count(),
        'disponibles':    qs.filter(statut='DISPONIBLE').count(),
        'consommes':      qs.filter(statut='CONSOMME').count(),
        'expires':        qs.filter(statut__in=['EXPIRE', 'ANNULE']).count(),
        'vendus_mois':    Ticket.objects.filter(date_creation__date__gte=debut_mois).count(),
        'consommes_mois': Ticket.objects.filter(statut='CONSOMME', date_consommation__date__gte=debut_mois).count(),
    }

    paginator = Paginator(qs.order_by('-date_creation'), 10)
    page_obj  = paginator.get_page(request.GET.get('page', 1))

    # Paramètres GET à conserver dans la pagination
    params_get = '&'.join([
        f"{k}={v}" for k, v in request.GET.items() if k != 'page' and v
    ])

    from apps.accounts.models import Agence
    return render(request, 'tickets/admin_tickets.html', {
        'tickets':    page_obj,
        'page_obj':   page_obj,
        'totaux':     totaux,
        'agences':    Agence.objects.filter(est_active=True).order_by('nom'),
        'filtres': {
            'search':     q,
            'statut':     statut,
            'agence':     agence,
            'date_debut': date_debut,
            'date_fin':   date_fin,
            'mois':       mois,
        },
        'extra_params': params_get,
    })

@login_required
def admin_tickets_stats(request):
    if not request.user.est_admin:
        return redirect('accounts:dashboard')

    aujourd_hui = timezone.now().date()
    debut_mois, fin_mois = _debut_fin_mois(aujourd_hui)

    # Statistiques globales
    stats = {
        'total_tickets':       Ticket.objects.count(),
        'disponibles':         Ticket.objects.filter(statut='DISPONIBLE').count(),
        'consommes_total':     Ticket.objects.filter(statut='CONSOMME').count(),
        'consommes_mois':      Ticket.objects.filter(statut='CONSOMME', date_consommation__date__gte=debut_mois).count(),
        'expires':             Ticket.objects.filter(statut='EXPIRE').count(),
        'annules':             Ticket.objects.filter(statut='ANNULE').count(),
        'qr_generes_mois':     CodeQR.objects.filter(date_creation__date__gte=debut_mois).count(),
        'qr_utilises_mois':    CodeQR.objects.filter(est_utilise=True, utilise_le__date__gte=debut_mois).count(),
    }

    # Consommations par jour (30 derniers jours)
    conso_jour = []
    for i in range(29, -1, -1):
        j  = aujourd_hui - timezone.timedelta(days=i)
        nb = Ticket.objects.filter(statut='CONSOMME', date_consommation__date=j).count()
        conso_jour.append({'date': j.strftime('%d/%m'), 'nb': nb})

    return render(request, 'tickets/admin_stats.html', {
        'stats':      stats,
        'conso_jour': conso_jour,
        'debut_mois': debut_mois,
        'fin_mois':   fin_mois,
    })

@login_required
def ticket_detail(request, pk):
    t = get_object_or_404(Ticket, pk=pk)
    if not (request.user.est_admin or t.proprietaire == request.user):
        return redirect('accounts:dashboard')
    return render(request, 'tickets/ticket_detail.html', {'ticket': t})


# ================================================================
# CAISSIER
# ================================================================
@login_required
def caissier_tickets(request):
    """Tickets vendus PAR CE CAISSIER uniquement."""
    if not (request.user.est_caissier or request.user.est_admin):
        return redirect('accounts:dashboard')

    from apps.tickets.models import Ticket
    from apps.accounts.models import Utilisateur

    # Seulement les tickets issus des transactions de ce caissier
    qs = Ticket.objects.filter(
        transaction__caissier=request.user
    ).select_related('proprietaire', 'transaction', 'restaurant_consommateur')

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
    params = _get_params()

    stats = {
        'total':       qs.count(),
        'disponibles': qs.filter(statut='DISPONIBLE').count(),
        'consommes':   qs.filter(statut='CONSOMME').count(),
        'expires':     qs.filter(statut='EXPIRE').count(),
    }

    # Clients éligibles (pas encore atteint leur limite ce mois)
    clients_ayant_atteint = (
        TransactionTicket.objects
        .filter(type_transaction='ACHAT', statut='TERMINEE', date_transaction__date__gte=debut_mois)
        .values('client_id')
        .annotate(nb=Count('id'))
        .filter(nb__gte=params['max_mensuel'])
        .values_list('client_id', flat=True)
    )
    clients = Utilisateur.objects.filter(
        type_utilisateur='CLIENT', est_actif=True,
    ).exclude(
        id__in=clients_ayant_atteint
    ).select_related('agence').order_by('nom', 'prenom')

    paginator = Paginator(qs.order_by('-date_creation'), 10)
    page_obj  = paginator.get_page(request.GET.get('page', 1))

    return render(request, 'tickets/caissier_tickets.html', {
        'tickets':     page_obj,
        'page_obj':    page_obj,
        'stats':       stats,
        'stats_pills': [
            ('disponibles', stats['disponibles'], '#28a745'),
            ('consommés',   stats['consommes'],   '#6c757d'),
            ('expirés/annulés', stats['expires'], '#dc3545'),
        ],
        'clients':     clients,
        'debut_mois':  debut_mois,
        'fin_mois':    fin_mois,
        'prix_ticket': params['prix_ticket'],
        'subvention':  params['subvention'],
        'min_tickets': params['min_tickets'],
        'max_tickets': params['max_tickets'],
        'max_mensuel': params['max_mensuel'],
        'statuts': [
            ('DISPONIBLE', 'Disponible'),
            ('CONSOMME',   'Consommé'),
            ('EXPIRE',     'Expiré'),
            ('ANNULE',     'Annulé'),
        ],
    })


# ================================================================
# CLIENT
# ================================================================
@login_required
def client_tickets(request):
    """Mes tickets — vue client."""
    if not request.user.est_client:
        return redirect('accounts:dashboard')

    aujourd_hui = timezone.now().date()
    debut_mois, fin_mois = _debut_fin_mois(aujourd_hui)

    tous = request.user.tickets.select_related('transaction', 'restaurant_consommateur')

    valides     = tous.filter(statut='DISPONIBLE', valide_de__lte=aujourd_hui, valide_jusqua__gte=aujourd_hui)
    consommes   = list(tous.filter(statut='CONSOMME').order_by('-date_consommation')[:20])
    expires     = tous.filter(statut__in=['EXPIRE', 'ANNULE']).order_by('-valide_jusqua')[:10]

    # Enrichir chaque ticket consommé avec le nom du plat (via Reservation TERMINE)
    from apps.restaurants.models import Reservation
    dates_consommes = {t.date_consommation.date() for t in consommes if t.date_consommation}
    plats_par_date = {}
    if dates_consommes:
        for r in Reservation.objects.filter(
            client=request.user, statut='TERMINE', date_reservation__in=list(dates_consommes)
        ).select_related('menu', 'restaurant'):
            plats_par_date.setdefault(r.date_reservation, {'menu': r.menu.nom, 'restaurant': r.restaurant.nom if r.restaurant else ''})
    for t in consommes:
        info = plats_par_date.get(t.date_consommation.date()) if t.date_consommation else None
        t.plat_nom = info['menu'] if info else None
        t.plat_restaurant = info['restaurant'] if info else None

    return render(request, 'tickets/client_tickets.html', {
        'tickets_valides':     valides,
        'tickets_consommes':   consommes,
        'tickets_expires':     expires,
        'nb_valides':          valides.count(),
        'nb_consommes_mois':   tous.filter(statut='CONSOMME', date_consommation__date__gte=debut_mois).count(),
        'aujourd_hui':         aujourd_hui,
        'debut_mois':          debut_mois,
        'fin_mois':            fin_mois,
    })

@login_required
def client_qrcode(request):
    """Page QR Code du client."""
    if not request.user.est_client:
        return redirect('accounts:dashboard')

    aujourd_hui = timezone.now().date()

    # QR code actif
    qr_actif = CodeQR.objects.filter(
        utilisateur=request.user,
        est_valide=True,
        est_utilise=False,
        expire_le__gt=timezone.now(),
    ).order_by('-date_creation').first()

    # Tickets valides disponibles
    tickets_valides = request.user.tickets.filter(
        statut='DISPONIBLE',
        valide_de__lte=aujourd_hui,
        valide_jusqua__gte=aujourd_hui,
    ).count()

    # Historique QR codes (5 derniers)
    historique_qr = CodeQR.objects.filter(
        utilisateur=request.user
    ).order_by('-date_creation')[:5]

    return render(request, 'tickets/client_qrcode.html', {
        'qr_actif':        qr_actif,
        'tickets_valides': tickets_valides,
        'historique_qr':   historique_qr,
        'aujourd_hui':     aujourd_hui,
    })

@login_required
@require_http_methods(["POST"])
def generer_qrcode(request):
    """Générer un nouveau QR code pour le client."""
    if not request.user.est_client:
        return JsonResponse({'error': 'Permission refusée'}, status=403)

    aujourd_hui = timezone.now().date()

    # Vérifier tickets disponibles
    if not request.user.tickets.filter(
        statut='DISPONIBLE',
        valide_de__lte=aujourd_hui,
        valide_jusqua__gte=aujourd_hui,
    ).exists():
        return JsonResponse({'error': 'Aucun ticket valide — impossible de générer un QR code'}, status=400)

    # Invalider les anciens QR
    CodeQR.invalider_codes_precedents(request.user)

    # Créer le nouveau
    try:
        qr = CodeQR(utilisateur=request.user)
        qr.save()
        return JsonResponse({
            'success': True,
            'message': 'QR Code généré avec succès',
            'code':    qr.code,
            'expire_le': qr.expire_le.isoformat(),
            'image_url': qr.image_qr.url if qr.image_qr else '',
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

@login_required
@require_http_methods(["POST"])
def invalider_qrcode(request, pk):
    """Invalider manuellement un QR code."""
    if not request.user.est_client:
        return JsonResponse({'error': 'Permission refusée'}, status=403)
    qr = get_object_or_404(CodeQR, pk=pk, utilisateur=request.user)
    qr.est_valide = False
    qr.save()
    return JsonResponse({'success': True, 'message': 'QR Code invalidé'})

