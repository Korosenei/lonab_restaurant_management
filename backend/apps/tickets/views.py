"""
Vues pour l'application tickets
"""
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib import messages
from django.db.models import Q, Count, Sum
from django.utils import timezone
from django.conf import settings
from .models import Ticket, CodeQR


def _debut_fin_mois(date=None):
    from dateutil.relativedelta import relativedelta
    d = date or timezone.now().date()
    debut = d.replace(day=1)
    fin   = debut + relativedelta(months=1) - relativedelta(days=1)
    return debut, fin


# ================================================================
# ADMIN
# ================================================================

@login_required
def admin_tickets_list(request):
    if not request.user.est_super_admin:
        return redirect('accounts:dashboard')

    qs = Ticket.objects.select_related('proprietaire', 'transaction', 'restaurant_consommateur')

    if q := request.GET.get('search'):
        qs = qs.filter(
            Q(numero_ticket__icontains=q) |
            Q(proprietaire__prenom__icontains=q) |
            Q(proprietaire__nom__icontains=q) |
            Q(proprietaire__matricule__icontains=q)
        )
    if statut := request.GET.get('statut'):
        qs = qs.filter(statut=statut)
    if mois := request.GET.get('mois'):
        try:
            y, m = mois.split('-')
            qs = qs.filter(valide_de__year=y, valide_de__month=m)
        except ValueError:
            pass

    debut_mois, _ = _debut_fin_mois()
    totaux = {
        'total':           qs.count(),
        'disponibles':     qs.filter(statut='DISPONIBLE').count(),
        'consommes':       qs.filter(statut='CONSOMME').count(),
        'expires':         qs.filter(statut='EXPIRE').count(),
        'vendus_mois':     Ticket.objects.filter(date_creation__date__gte=debut_mois).count(),
        'consommes_mois':  Ticket.objects.filter(statut='CONSOMME', date_consommation__date__gte=debut_mois).count(),
    }

    return render(request, 'tickets/admin_tickets.html', {
        'tickets': qs.order_by('-date_creation')[:300],
        'totaux':  totaux,
    })


@login_required
def admin_tickets_stats(request):
    if not request.user.est_super_admin:
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
    if not (request.user.est_super_admin or t.proprietaire == request.user):
        return redirect('accounts:dashboard')
    return render(request, 'tickets/ticket_detail.html', {'ticket': t})


# ================================================================
# CAISSIER
# ================================================================

@login_required
def caissier_tickets(request):
    """Liste de tous les tickets + stats + modal vente."""
    if not (request.user.est_caissier or request.user.est_super_admin):
        return redirect('accounts:dashboard')

    qs = Ticket.objects.select_related('proprietaire', 'restaurant_consommateur')

    if q := request.GET.get('search'):
        qs = qs.filter(
            Q(numero_ticket__icontains=q) |
            Q(proprietaire__prenom__icontains=q) |
            Q(proprietaire__nom__icontains=q) |
            Q(proprietaire__matricule__icontains=q)
        )
    if statut := request.GET.get('statut'):
        qs = qs.filter(statut=statut)
    if mois := request.GET.get('mois'):
        try:
            y, m = mois.split('-')
            qs = qs.filter(valide_de__year=y, valide_de__month=m)
        except ValueError:
            pass

    debut_mois, fin_mois = _debut_fin_mois()
    today = timezone.now().date()

    stats = {
        'disponibles':    Ticket.objects.filter(statut='DISPONIBLE').count(),
        'consommes_mois': Ticket.objects.filter(statut='CONSOMME', date_consommation__date__gte=debut_mois).count(),
        'vendus_mois':    Ticket.objects.filter(date_creation__date__gte=debut_mois).count(),
        'expires':        Ticket.objects.filter(statut__in=['EXPIRE', 'ANNULE']).count(),
    }

    # Clients pour le modal de vente
    from apps.accounts.models import Utilisateur
    clients = Utilisateur.objects.filter(
        type_utilisateur='CLIENT', est_actif=True
    ).select_related('agence').order_by('nom', 'prenom')

    return render(request, 'tickets/caissier_tickets.html', {
        'tickets':       qs.order_by('-date_creation')[:500],
        'total_tickets': qs.count(),
        'stats':         stats,
        'clients':       clients,
        'debut_mois':    debut_mois,
        'fin_mois':      fin_mois,
        'prix_ticket':   getattr(settings, 'TICKET_PRICE', 500),
        'subvention':    getattr(settings, 'TICKET_SUBSIDY', 1500),
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