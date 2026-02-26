"""
Vues pour l'application settings — paramètres système et audit
"""
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.utils import timezone
from dateutil.relativedelta import relativedelta
from .models import ParametresSysteme, JournalAudit, JourFerie


def _admin_required(request):
    """Retourne True si l'accès doit être refusé."""
    if not request.user.is_authenticated or not request.user.est_admin:
        return True
    return False

def _base_ctx(request):
    """Contexte commun à toutes les vues admin."""
    ctx = {
        'annee_courante': timezone.now().year,
        'notifications': [],
        'unread_notifications_count': 0,
    }
    try:
        from apps.notifs.models import Notification
        ctx['notifications'] = Notification.objects.filter(
            destinataire=request.user, est_lu=False
        ).order_by('-cree_le')[:5]
        ctx['unread_notifications_count'] = Notification.objects.filter(
            destinataire=request.user, est_lu=False
        ).count()
    except Exception:
        pass
    return ctx

def _stats_base(aujourd_hui=None):
    """Calcule les stats communes (même logique que dashboard_admin)."""
    from apps.accounts.models import Utilisateur, Direction, Agence
    if not aujourd_hui:
        aujourd_hui = timezone.now().date()
    debut_mois = aujourd_hui.replace(day=1)

    stats = {}
    stats['total_employes'] = Utilisateur.objects.filter(type_utilisateur='CLIENT', est_actif=True).count()
    stats['nouveaux_employes_mois'] = Utilisateur.objects.filter(
        type_utilisateur='CLIENT', date_inscription__date__gte=debut_mois
    ).count()
    stats['total_directions'] = Direction.objects.count()
    stats['directions_actives'] = Direction.objects.filter(est_active=True).count()
    stats['total_agences'] = Agence.objects.count()
    stats['agences_actives'] = Agence.objects.filter(est_active=True).count()

    try:
        from apps.restaurants.models import Restaurant
        stats['total_restaurants'] = Restaurant.objects.count()
        stats['restaurants_actifs'] = Restaurant.objects.filter(statut='ACTIF').count()
    except Exception:
        stats['total_restaurants'] = 0
        stats['restaurants_actifs'] = 0

    try:
        from apps.transactions.models import TransactionTicket
        from apps.tickets.models import Ticket
        txs = TransactionTicket.objects.filter(date_transaction__date__gte=debut_mois, statut='TERMINE')
        stats['tickets_vendus_mois'] = sum(t.nombre_tickets for t in txs)
        stats['revenu_mois'] = sum(t.montant_total for t in txs)
        stats['tickets_consommes_mois'] = Ticket.objects.filter(
            statut='CONSOMME', date_consommation__date__gte=debut_mois
        ).count()
        stats['transactions_recentes'] = TransactionTicket.objects.select_related('client').order_by('-date_transaction')[:15]
    except Exception:
        stats['tickets_vendus_mois'] = 0
        stats['revenu_mois'] = 0
        stats['tickets_consommes_mois'] = 0
        stats['transactions_recentes'] = []

    # Directions principales avec pourcentage
    from apps.accounts.models import Direction
    dirs = Direction.objects.filter(est_active=True).annotate(
        nombre_employes=Count('employes', filter=Q(employes__type_utilisateur='CLIENT', employes__est_actif=True))
    ).order_by('-nombre_employes')[:5]
    max_nb = dirs.first().nombre_employes if dirs.exists() else 1
    for d in dirs:
        d.pourcentage = (d.nombre_employes / max_nb * 100) if max_nb > 0 else 0
    stats['directions_principales'] = dirs

    return stats

# ════════════════════════════════════════════════════════════════
# Paramètres système
# ════════════════════════════════════════════════════════════════
@login_required
def admin_settings(request):
    if _admin_required(request):
        messages.warning(request, 'Accès refusé.')
        return redirect('accounts:dashboard')

    params = ParametresSysteme.charger()

    if request.method == 'POST':
        try:
            # Tickets
            params.tickets_min_par_transaction = int(request.POST.get('tickets_min_par_transaction', 1))
            params.tickets_max_par_transaction = int(request.POST.get('tickets_max_par_transaction', 20))
            params.transactions_max_par_mois = int(request.POST.get('transactions_max_par_mois', 1))
            params.duree_validite_qr_code_minutes = int(request.POST.get('duree_validite_qr_code_minutes', 3))

            # Tarification
            params.prix_ticket = request.POST.get('prix_ticket', 500)
            params.prix_repas_complet = request.POST.get('prix_repas_complet', 2000)
            params.subvention_ticket = request.POST.get('subvention_ticket', 1500)

            # Notifications (checkboxes)
            params.envoyer_notifications_achat = 'envoyer_notifications_achat' in request.POST
            params.envoyer_notifications_consommation = 'envoyer_notifications_consommation' in request.POST
            params.envoyer_notifications_programmation = 'envoyer_notifications_programmation' in request.POST
            params.envoyer_notifications_menu = 'envoyer_notifications_menu' in request.POST
            params.email_notifications_expediteur = request.POST.get('email_notifications_expediteur', 'noreply@lonab.com').strip()

            # Entreprise
            params.nom_entreprise = request.POST.get('nom_entreprise', 'LONAB').strip()
            params.nom_mutuelle = request.POST.get('nom_mutuelle', 'MUTRALO').strip()
            params.email_support = request.POST.get('email_support', 'support@lonab.com').strip()
            params.telephone_support = request.POST.get('telephone_support', '').strip()

            # Maintenance
            params.mode_maintenance = 'mode_maintenance' in request.POST
            params.message_maintenance = request.POST.get('message_maintenance', '').strip()

            params.modifie_par = request.user
            params.full_clean()
            params.save()

            # Journal d'audit
            JournalAudit.objects.create(
                utilisateur=request.user,
                action='MODIFICATION',
                modele='ParametresSysteme',
                objet_id=1,
                description=f'Paramètres système modifiés par {request.user.get_full_name()}',
                adresse_ip=_get_client_ip(request),
            )

            messages.success(request, 'Paramètres enregistrés avec succès.')
            return redirect('settings:admin_settings')

        except Exception as e:
            messages.error(request, f'Erreur : {e}')

    return render(request, 'settings/admin_settings.html', {
        'params': params,
        'notifications': _get_notifs(request),
        'unread_notifications_count': _count_unread(request),
    })


# ════════════════════════════════════════════════════════════════
# Journal d'Audit
# ════════════════════════════════════════════════════════════════
@login_required
def admin_audit(request):
    if _admin_required(request):
        messages.warning(request, 'Accès refusé.')
        return redirect('accounts:dashboard')

    aujourd_hui = timezone.now().date()
    qs = JournalAudit.objects.select_related('utilisateur').order_by('-cree_le')

    # Filtres
    search = request.GET.get('search', '').strip()
    action = request.GET.get('action', '').strip()
    modele = request.GET.get('modele', '').strip()
    date_debut = request.GET.get('date_debut', '').strip()
    date_fin = request.GET.get('date_fin', '').strip()

    if search:
        qs = qs.filter(
            Q(description__icontains=search) |
            Q(utilisateur__prenom__icontains=search) |
            Q(utilisateur__nom__icontains=search) |
            Q(modele__icontains=search)
        )
    if action:
        qs = qs.filter(action=action)
    if modele:
        qs = qs.filter(modele__icontains=modele)
    if date_debut:
        qs = qs.filter(cree_le__date__gte=date_debut)
    if date_fin:
        qs = qs.filter(cree_le__date__lte=date_fin)

    # Stats
    total_entrees = JournalAudit.objects.count()
    entrees_aujourd_hui = JournalAudit.objects.filter(cree_le__date=aujourd_hui).count()
    entrees_semaine = JournalAudit.objects.filter(cree_le__date__gte=aujourd_hui - timezone.timedelta(days=6)).count()

    from apps.accounts.models import Utilisateur
    nb_utilisateurs_actifs = Utilisateur.objects.filter(est_actif=True).count()

    paginator = Paginator(qs, 50)
    page_obj = paginator.get_page(request.GET.get('page', 1))

    return render(request, 'settings/admin_audit.html', {
        'entrees': page_obj,
        'page_obj': page_obj,
        'total_entrees': total_entrees,
        'entrees_aujourd_hui': entrees_aujourd_hui,
        'entrees_semaine': entrees_semaine,
        'nb_utilisateurs_actifs': nb_utilisateurs_actifs,
        'filtres': {'search': search, 'action': action, 'modele': modele, 'date_debut': date_debut, 'date_fin': date_fin},
        'notifications': _get_notifs(request),
        'unread_notifications_count': _count_unread(request),
    })


# ════════════════════════════════════════════════════════════════
# Jours fériés (CRUD JSON)
# ════════════════════════════════════════════════════════════════
@login_required
@require_http_methods(['POST'])
def jour_ferie_create(request):
    if _admin_required(request):
        return JsonResponse({'error': 'Accès refusé'}, status=403)
    try:
        jf = JourFerie.objects.create(
            nom=request.POST.get('nom', '').strip(),
            date=request.POST.get('date'),
            recurrent='recurrent' in request.POST,
            description=request.POST.get('description', '').strip(),
            actif=True,
        )
        return JsonResponse({'success': True, 'message': f'Jour férié « {jf.nom} » créé', 'id': jf.id})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

@login_required
@require_http_methods(['POST'])
def jour_ferie_delete(request, pk):
    if _admin_required(request):
        return JsonResponse({'error': 'Accès refusé'}, status=403)
    try:
        jf = JourFerie.objects.get(pk=pk)
        nom = jf.nom
        jf.delete()
        return JsonResponse({'success': True, 'message': f'Jour férié « {nom} » supprimé'})
    except JourFerie.DoesNotExist:
        return JsonResponse({'error': 'Introuvable'}, status=404)


# ════════════════════════════════════════════════════════════════
@login_required
def admin_overview(request):
    if _admin_required(request):
        messages.warning(request, 'Accès refusé.')
        return redirect('accounts:dashboard')

    try:
        params = ParametresSysteme.charger()
        mode_maintenance = params.mode_maintenance
    except Exception:
        mode_maintenance = False

    ctx = _base_ctx(request)
    ctx.update(_stats_base())
    ctx['mode_maintenance'] = mode_maintenance

    return render(request, 'settings/admin_overview.html', ctx)

@login_required
def admin_reports(request):
    if _admin_required(request):
        messages.warning(request, 'Accès refusé.')
        return redirect('accounts:dashboard')

    from apps.accounts.models import Agence
    aujourd_hui = timezone.now().date()

    # Filtres
    date_debut = request.GET.get('date_debut', aujourd_hui.replace(day=1).isoformat())
    date_fin = request.GET.get('date_fin', aujourd_hui.isoformat())
    agence_id = request.GET.get('agence', '')
    type_rapport = request.GET.get('type', '')

    agences_qs = Agence.objects.filter(est_active=True)

    # Rapport par agence
    rapport_agences = []
    try:
        from apps.tickets.models import Ticket
        from apps.transactions.models import TransactionTicket
        params = ParametresSysteme.charger()

        for a in agences_qs:
            tickets_achetes = Ticket.objects.filter(
                proprietaire__agence=a,
                date_achat__date__gte=date_debut,
                date_achat__date__lte=date_fin
            ).count()
            tickets_consommes = Ticket.objects.filter(
                proprietaire__agence=a,
                statut='CONSOMME',
                date_consommation__date__gte=date_debut,
                date_consommation__date__lte=date_fin
            ).count()
            txs = TransactionTicket.objects.filter(
                client__agence=a,
                statut='TERMINE',
                date_transaction__date__gte=date_debut,
                date_transaction__date__lte=date_fin
            )
            montant_total = sum(t.montant_total for t in txs)
            subvention = tickets_consommes * float(params.subvention_ticket)

            a.tickets_achetes = tickets_achetes
            a.tickets_consommes = tickets_consommes
            a.montant_total = montant_total
            a.subvention = subvention
            a.nb_employes = a.employes.filter(type_utilisateur='CLIENT', est_actif=True).count()
            rapport_agences.append(a)
    except Exception:
        pass

    # Données graphe mensuel (12 mois)
    graph_mensuel_tickets = []
    graph_mensuel_montants = []
    try:
        from apps.tickets.models import Ticket
        from apps.transactions.models import TransactionTicket
        debut_annee = aujourd_hui.replace(month=1, day=1)
        for mois in range(1, 13):
            debut_m = aujourd_hui.replace(month=mois, day=1)
            fin_m = debut_m + relativedelta(months=1) - relativedelta(days=1)
            nb = Ticket.objects.filter(date_achat__date__gte=debut_m, date_achat__date__lte=fin_m).count()
            txs = TransactionTicket.objects.filter(statut='TERMINE', date_transaction__date__gte=debut_m, date_transaction__date__lte=fin_m)
            montant = sum(t.montant_total for t in txs)
            graph_mensuel_tickets.append(nb)
            graph_mensuel_montants.append(float(montant))
    except Exception:
        graph_mensuel_tickets = [0] * 12
        graph_mensuel_montants = [0.0] * 12

    ctx = _base_ctx(request)
    ctx.update({
        'agences': agences_qs,
        'rapport_agences': rapport_agences,
        'graph_mensuel_tickets': graph_mensuel_tickets,
        'graph_mensuel_montants': graph_mensuel_montants,
        'filtres': {'date_debut': date_debut, 'date_fin': date_fin, 'agence': agence_id, 'type': type_rapport},
    })
    return render(request, 'settings/admin_reports.html', ctx)

@login_required
def admin_audit(request):
    if not request.user.is_superuser:
        messages.warning(request, "Accès refusé.")
        return redirect('accounts:dashboard')

    audits = JournalAudit.objects.select_related('utilisateur').all()

    return render(request, 'settings/admin_audit.html', {
        'audits': audits
    })

# ════════════════════════════════════════════════════════════════
# API — Paramètres publics (pour les apps internes)
# ════════════════════════════════════════════════════════════════
def api_params(request):
    """Retourne les paramètres publics en JSON (usage interne)."""
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Non authentifié'}, status=401)
    params = ParametresSysteme.charger()
    return JsonResponse({
        'tickets_min': params.tickets_min_par_transaction,
        'tickets_max': params.tickets_max_par_transaction,
        'transactions_max_mois': params.transactions_max_par_mois,
        'prix_ticket': float(params.prix_ticket),
        'prix_repas': float(params.prix_repas_complet),
        'subvention': float(params.subvention_ticket),
        'qr_validite_minutes': params.duree_validite_qr_code_minutes,
        'mode_maintenance': params.mode_maintenance,
        'nom_entreprise': params.nom_entreprise,
        'nom_mutuelle': params.nom_mutuelle,
    })


# ════════════════════════════════════════════════════════════════
# Helpers
# ════════════════════════════════════════════════════════════════
def _get_client_ip(request):
    x_forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded:
        return x_forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')

def _get_notifs(request):
    try:
        from apps.notifs.models import Notification
        return Notification.objects.filter(destinataire=request.user, est_lu=False).order_by('-cree_le')[:5]
    except Exception:
        return []

def _count_unread(request):
    try:
        from apps.notifs.models import Notification
        return Notification.objects.filter(destinataire=request.user, est_lu=False).count()
    except Exception:
        return 0