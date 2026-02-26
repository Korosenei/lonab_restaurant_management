
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.db.models import Sum, Count, Q


# ────────────────────────────────────────────────────────────
#  HELPERS
# ────────────────────────────────────────────────────────────
def _debut_fin_mois(date):
    debut = date.replace(day=1)
    if date.month == 12:
        fin = date.replace(year=date.year + 1, month=1, day=1)
    else:
        fin = date.replace(month=date.month + 1, day=1)
    return debut, fin


def _base_ctx(request):
    """Contexte commun à tous les dashboards (notifications)."""
    ctx = {'aujourd_hui': timezone.now().date(), 'unread_notifications_count': 0, 'notifications': []}
    try:
        from apps.notifs.models import Notification
        notifs = Notification.objects.filter(destinataire=request.user, est_lue=False)
        ctx['unread_notifications_count'] = notifs.count()
        ctx['notifications'] = notifs.order_by('-date_creation')[:5]
    except Exception:
        pass
    return ctx


# ============================================
# Vues de tableau de bord
# ============================================
@login_required
def dashboard_redirection(request):
    """Rediriger vers le tableau de bord approprié selon le type d'utilisateur"""
    utilisateur = request.user

    if utilisateur.est_admin:
        return redirect('accounts:admin_dashboard')
    elif utilisateur.est_caissier:
        return redirect('accounts:caissier_dashboard')
    elif utilisateur.est_gestionnaire_restaurant:
        return redirect('accounts:restaurant_dashboard')
    else:  # CLIENT
        return redirect('accounts:client_dashboard')

# ============================================================
#  1. ADMIN DASHBOARD
# ============================================================
@login_required
def admin_dashboard(request):
    if not request.user.est_admin:
        return redirect('accounts:client_dashboard')

    from apps.accounts.models import Utilisateur, Direction, Agence
    from apps.tickets.models import Ticket
    from apps.transactions.models import TransactionTicket
    from apps.restaurants.models import Restaurant

    aujourd_hui = timezone.now().date()
    debut_mois, fin_mois = _debut_fin_mois(aujourd_hui)
    debut_semaine = aujourd_hui - timezone.timedelta(days=aujourd_hui.weekday())
    il_y_a_30j = aujourd_hui - timezone.timedelta(days=29)

    # ── Stats globales ─────────────────────────────────────
    total_employes     = Utilisateur.objects.filter(est_actif=True).count()
    nouveaux_mois      = Utilisateur.objects.filter(date_inscription__gte=debut_mois).count()
    total_directions   = Direction.objects.count()
    directions_actives = Direction.objects.filter(est_active=True).count()
    total_agences      = Agence.objects.count()
    agences_actives    = Agence.objects.filter(est_active=True).count()
    total_restaurants  = Restaurant.objects.count()
    restaurants_actifs = Restaurant.objects.filter(statut='ACTIF').count()

    tickets_mois = Ticket.objects.filter(
        valide_de__gte=debut_mois
    ).aggregate(t=Count('id'))['t'] or 0

    tickets_consommes_mois = Ticket.objects.filter(
        statut='CONSOMME', date_consommation__date__gte=debut_mois
    ).count()

    revenu_mois = TransactionTicket.objects.filter(
        statut='TERMINEE', date_transaction__date__gte=debut_mois
    ).aggregate(s=Sum('montant_total'))['s'] or 0

    # ── Graphe 30 jours — tickets vendus ──────────────────
    graph_labels, graph_values = [], []
    for i in range(29, -1, -1):
        j = aujourd_hui - timezone.timedelta(days=i)
        nb = Ticket.objects.filter(valide_de=j).count()
        graph_labels.append(j.strftime('%d/%m'))
        graph_values.append(nb)

    # ── Transactions récentes ─────────────────────────────
    transactions_recentes = TransactionTicket.objects.select_related(
        'client', 'caissier'
    ).order_by('-date_transaction')[:8]

    # ── Répartition par type d'utilisateur ────────────────
    types_users = list(
        Utilisateur.objects.values('type_utilisateur')
        .annotate(nb=Count('id')).order_by('-nb')
    )

    # ── Activité systeme (dernières connexions) ────────────
    derniers_connectes = Utilisateur.objects.filter(
        derniere_connexion__isnull=False
    ).order_by('-derniere_connexion')[:5]

    ctx = _base_ctx(request)
    ctx.update({
        'total_employes': total_employes,
        'nouveaux_mois': nouveaux_mois,
        'total_directions': total_directions,
        'directions_actives': directions_actives,
        'total_agences': total_agences,
        'agences_actives': agences_actives,
        'total_restaurants': total_restaurants,
        'restaurants_actifs': restaurants_actifs,
        'tickets_mois': tickets_mois,
        'tickets_consommes_mois': tickets_consommes_mois,
        'revenu_mois': revenu_mois,
        'graph_labels': graph_labels,
        'graph_values': graph_values,
        'transactions_recentes': transactions_recentes,
        'types_users': types_users,
        'derniers_connectes': derniers_connectes,
        'taux_consommation': round(tickets_consommes_mois / tickets_mois * 100, 1) if tickets_mois else 0,
    })
    return render(request, 'dashboards/admin_dashboard.html', ctx)


# ============================================================
#  2. CAISSIER DASHBOARD
# ============================================================
@login_required
def caissier_dashboard(request):
    if not (request.user.est_caissier or request.user.est_admin):
        return redirect('accounts:client_dashboard')

    from apps.transactions.models import TransactionTicket
    from apps.tickets.models import Ticket, CodeQR

    aujourd_hui = timezone.now().date()
    debut_mois, _ = _debut_fin_mois(aujourd_hui)
    debut_semaine = aujourd_hui - timezone.timedelta(days=aujourd_hui.weekday())

    mes_transactions = TransactionTicket.objects.filter(caissier=request.user)

    # ── Stats ──────────────────────────────────────────────
    stats = {
        'aujourd_hui':  mes_transactions.filter(date_transaction__date=aujourd_hui).count(),
        'cette_semaine': mes_transactions.filter(
            statut='TERMINEE', date_transaction__date__gte=debut_semaine
        ).count(),
        'tickets_mois': mes_transactions.filter(
            statut='TERMINEE', date_transaction__date__gte=debut_mois
        ).aggregate(t=Sum('nombre_tickets'))['t'] or 0,
        'ca_mois': mes_transactions.filter(
            statut='TERMINEE', date_transaction__date__gte=debut_mois
        ).aggregate(s=Sum('montant_total'))['s'] or 0,
        'en_attente': mes_transactions.filter(statut='EN_ATTENTE').count(),
        'terminees': mes_transactions.filter(
            statut='TERMINEE', date_transaction__date=aujourd_hui
        ).count(),
    }

    # ── Graphe 30 jours ────────────────────────────────────
    graph_labels, graph_tickets, graph_montants = [], [], []
    for i in range(29, -1, -1):
        j = aujourd_hui - timezone.timedelta(days=i)
        agg = mes_transactions.filter(
            statut='TERMINEE', date_transaction__date=j
        ).aggregate(t=Sum('nombre_tickets'), s=Sum('montant_total'))
        graph_labels.append(j.strftime('%d/%m'))
        graph_tickets.append(agg['t'] or 0)
        graph_montants.append(float(agg['s'] or 0))

    # ── Transactions récentes ─────────────────────────────
    recentes = mes_transactions.select_related('client').order_by('-date_transaction')[:10]

    # ── Top clients du mois ───────────────────────────────
    top_clients = mes_transactions.filter(
        statut='TERMINEE', date_transaction__date__gte=debut_mois
    ).values('client__prenom', 'client__nom', 'client__matricule').annotate(
        total_tickets=Sum('nombre_tickets'),
        total_montant=Sum('montant_total')
    ).order_by('-total_tickets')[:5]

    # ── QR Code caissier ──────────────────────────────────
    qr_caissier = CodeQR.objects.filter(
        utilisateur=request.user,
        est_valide=True,
        est_utilise=False,
        expire_le__gt=timezone.now(),
    ).order_by('-date_creation').first()
    if not qr_caissier:
        try:
            CodeQR.invalider_codes_precedents(request.user)
            qr_caissier = CodeQR(utilisateur=request.user)
            qr_caissier.save()
        except Exception:
            qr_caissier = None

    ctx = _base_ctx(request)
    ctx.update({
        'stats': stats,
        'graph_labels': graph_labels,
        'graph_tickets': graph_tickets,
        'graph_montants': graph_montants,
        'recentes': recentes,
        'top_clients': top_clients,
        'qr_caissier': qr_caissier,
    })
    return render(request, 'dashboards/caissier_dashboard.html', ctx)


# ============================================================
#  3. GESTIONNAIRE DASHBOARD
# ============================================================
@login_required
def gestionnaire_dashboard(request):
    if not request.user.est_gestionnaire_restaurant:
        return redirect('accounts:client_dashboard')

    restaurant = getattr(request.user, 'restaurant_gere', None)
    if not restaurant:
        from django.contrib import messages
        messages.error(request, "Aucun restaurant associé à votre compte.")
        return redirect('accounts:profile')

    from apps.restaurants.models import Menu, Reservation

    aujourd_hui = timezone.now().date()
    debut_mois, _ = _debut_fin_mois(aujourd_hui)
    debut_semaine = aujourd_hui - timezone.timedelta(days=aujourd_hui.weekday())

    # ── Tickets consommés ─────────────────────────────────
    tickets_qs = restaurant.tickets_consommes.all()
    tickets_aujourd_hui = tickets_qs.filter(date_consommation__date=aujourd_hui).count()
    tickets_semaine     = tickets_qs.filter(date_consommation__date__gte=debut_semaine).count()
    tickets_mois        = tickets_qs.filter(date_consommation__date__gte=debut_mois).count()

    # ── Réservations du jour ──────────────────────────────
    reservations_jour = Reservation.objects.filter(
        restaurant=restaurant, date_reservation=aujourd_hui
    ).select_related('client', 'menu').order_by('statut')

    nb_attente  = reservations_jour.filter(statut='EN_ATTENTE').count()
    nb_confirme = reservations_jour.filter(statut='CONFIRME').count()
    nb_termine  = reservations_jour.filter(statut='TERMINE').count()

    # ── Menus du jour ─────────────────────────────────────
    menus_aujourd_hui = Menu.objects.filter(
        restaurant=restaurant, date=aujourd_hui, est_disponible=True
    ).order_by('nom')

    # ── Graphe 14 jours ───────────────────────────────────
    graph_labels, graph_values = [], []
    for i in range(13, -1, -1):
        j = aujourd_hui - timezone.timedelta(days=i)
        nb = tickets_qs.filter(date_consommation__date=j).count()
        graph_labels.append(j.strftime('%d/%m'))
        graph_values.append(nb)

    # ── Derniers scans ────────────────────────────────────
    derniers_scans = tickets_qs.filter(
        date_consommation__date=aujourd_hui
    ).select_related('proprietaire', 'proprietaire__agence').order_by('-date_consommation')[:10]

    # ── Stats menus ───────────────────────────────────────
    total_menus       = Menu.objects.filter(restaurant=restaurant, date=aujourd_hui).count()
    menus_disponibles = menus_aujourd_hui.count()
    menus_epuises     = Menu.objects.filter(
        restaurant=restaurant, date=aujourd_hui, est_disponible=False
    ).count()

    ctx = _base_ctx(request)
    ctx.update({
        'restaurant': restaurant,
        'tickets_aujourd_hui': tickets_aujourd_hui,
        'tickets_semaine': tickets_semaine,
        'tickets_mois': tickets_mois,
        'reservations_jour': reservations_jour,
        'nb_attente': nb_attente,
        'nb_confirme': nb_confirme,
        'nb_termine': nb_termine,
        'menus_aujourd_hui': menus_aujourd_hui,
        'total_menus': total_menus,
        'menus_disponibles': menus_disponibles,
        'menus_epuises': menus_epuises,
        'graph_labels': graph_labels,
        'graph_values': graph_values,
        'derniers_scans': derniers_scans,
    })
    return render(request, 'dashboards/gestionnaire_dashboard.html', ctx)


# ============================================================
#  4. CLIENT DASHBOARD
# ============================================================
@login_required
def client_dashboard(request):
    from apps.tickets.models import Ticket, CodeQR
    from apps.restaurants.models import Reservation, Menu

    aujourd_hui = timezone.now().date()
    debut_mois, _ = _debut_fin_mois(aujourd_hui)

    mes_tickets = Ticket.objects.filter(proprietaire=request.user)

    # ── Stats ──────────────────────────────────────────────
    tickets_disponibles = mes_tickets.filter(statut='DISPONIBLE').count()
    tickets_consommes   = mes_tickets.filter(statut='CONSOMME').count()
    tickets_expires     = mes_tickets.filter(statut='EXPIRE').count()
    total_tickets       = mes_tickets.count()

    valeur_disponible = mes_tickets.filter(
        statut='DISPONIBLE'
    ).aggregate(s=Sum('prix_paye'))['s'] or 0

    valeur_totale = mes_tickets.aggregate(s=Sum('prix_paye'))['s'] or 0

    # ── Réservations ─────────────────────────────────────
    mes_reservations = Reservation.objects.filter(
        client=request.user
    ).select_related('restaurant', 'menu')
    reservations_actives = mes_reservations.filter(
        statut__in=['EN_ATTENTE', 'CONFIRME']
    ).count()
    prochaine_reservation = mes_reservations.filter(
        statut__in=['EN_ATTENTE', 'CONFIRME'],
        date_reservation__gte=aujourd_hui
    ).order_by('date_reservation').first()

    # ── Menus du jour (agence du client) ─────────────────
    menus_jour = []
    if request.user.agence:
        from apps.restaurants.models import PlanningRestaurant
        plannings_actifs = PlanningRestaurant.objects.filter(
            agence=request.user.agence,
            date_debut__lte=timezone.now(),
            date_fin__gte=timezone.now(),
            est_actif=True,
        ).values_list('restaurant_id', flat=True)
        menus_jour = Menu.objects.filter(
            restaurant_id__in=plannings_actifs,
            date=aujourd_hui,
            est_disponible=True
        ).select_related('restaurant')[:6]

    # ── Historique des 5 derniers tickets consommés ──────
    derniers_consommes = mes_tickets.filter(
        statut='CONSOMME'
    ).order_by('-date_consommation')[:5]

    # ── QR Code actif ─────────────────────────────────────
    code_qr = CodeQR.objects.filter(
        utilisateur=request.user,
        est_valide=True,
        est_utilise=False,
        expire_le__gt=timezone.now(),
    ).order_by('-date_creation').first()

    # ── Graphe 7 jours consommations ─────────────────────
    graph_labels, graph_values = [], []
    for i in range(6, -1, -1):
        j = aujourd_hui - timezone.timedelta(days=i)
        nb = mes_tickets.filter(statut='CONSOMME', date_consommation__date=j).count()
        graph_labels.append(j.strftime('%a'))
        graph_values.append(nb)

    ctx = _base_ctx(request)
    ctx.update({
        'tickets_disponibles': tickets_disponibles,
        'tickets_consommes': tickets_consommes,
        'tickets_expires': tickets_expires,
        'total_tickets': total_tickets,
        'valeur_disponible': valeur_disponible,
        'valeur_totale': valeur_totale,
        'reservations_actives': reservations_actives,
        'prochaine_reservation': prochaine_reservation,
        'menus_jour': menus_jour,
        'derniers_consommes': derniers_consommes,
        'code_qr': code_qr,
        'graph_labels': graph_labels,
        'graph_values': graph_values,
        # alias compatibilité anciens templates
        'nombre_tickets_disponibles': tickets_disponibles,
        'nombre_tickets_consommes': tickets_consommes,
        'nombre_reservations_actives': reservations_actives,
    })
    return render(request, 'dashboards/client_dashboard.html', ctx)

