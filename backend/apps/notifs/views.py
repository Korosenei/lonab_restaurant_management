"""
Vues pour l'application notifs — gestion des notifications
"""
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.core.paginator import Paginator
from django.db.models import Q
from django.utils import timezone
from .models import Notification


def _admin_required(request):
    return not request.user.is_authenticated or not request.user.est_admin


# ════════════════════════════════════════════════════════════════
# Admin — Centre de notifications
# ════════════════════════════════════════════════════════════════
@login_required
def admin_notifications(request):
    if _admin_required(request):
        messages.warning(request, 'Accès refusé.')
        return redirect('accounts:dashboard')

    aujourd_hui = timezone.now().date()

    # Filtres
    search = request.GET.get('search', '').strip()
    type_n = request.GET.get('type', '').strip()
    priorite = request.GET.get('priorite', '').strip()
    lu = request.GET.get('lu', '').strip()

    qs = Notification.objects.select_related('destinataire').order_by('-cree_le')

    if search:
        qs = qs.filter(Q(titre__icontains=search) | Q(message__icontains=search) |
                       Q(destinataire__prenom__icontains=search) | Q(destinataire__nom__icontains=search))
    if type_n:
        qs = qs.filter(type_notification=type_n)
    if priorite:
        qs = qs.filter(priorite=priorite)
    if lu == '0':
        qs = qs.filter(est_lu=False)
    elif lu == '1':
        qs = qs.filter(est_lu=True)

    # Stats
    total_notifs = Notification.objects.count()
    notifs_non_lues = Notification.objects.filter(est_lu=False).count()
    notifs_aujourd_hui = Notification.objects.filter(cree_le__date=aujourd_hui).count()
    notifs_semaine = Notification.objects.filter(cree_le__date__gte=aujourd_hui - timezone.timedelta(days=6)).count()

    paginator = Paginator(qs, 30)
    page_obj = paginator.get_page(request.GET.get('page', 1))

    return render(request, 'notifs/admin_notifications.html', {
        'notifs': page_obj,
        'page_obj': page_obj,
        'total_notifs': total_notifs,
        'notifs_non_lues': notifs_non_lues,
        'notifs_aujourd_hui': notifs_aujourd_hui,
        'notifs_semaine': notifs_semaine,
        'filtres': {'search': search, 'type': type_n, 'priorite': priorite, 'lu': lu},
        'notifications': _mes_notifs(request),
        'unread_notifications_count': notifs_non_lues,
    })


# ════════════════════════════════════════════════════════════════
# Actions sur les notifications
# ════════════════════════════════════════════════════════════════
@login_required
@require_http_methods(['POST'])
def marquer_lu(request, pk):
    """Marque une notification comme lue."""
    n = get_object_or_404(Notification, pk=pk)
    # Admin peut tout marquer ; les autres seulement les leurs
    if not request.user.est_admin and n.destinataire != request.user:
        return JsonResponse({'error': 'Accès refusé'}, status=403)
    n.marquer_comme_lu()
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': True, 'message': 'Notification marquée comme lue'})
    return redirect(request.META.get('HTTP_REFERER', 'notifs:admin_notifications'))

@login_required
@require_http_methods(['POST'])
def marquer_tout_lu(request):
    """Marque toutes les notifications de l'utilisateur comme lues."""
    if request.user.est_admin:
        # Admin marque tout le système
        Notification.objects.filter(est_lu=False).update(est_lu=True, lu_le=timezone.now())
        messages.success(request, 'Toutes les notifications ont été marquées comme lues.')
    else:
        Notification.objects.filter(destinataire=request.user, est_lu=False).update(est_lu=True, lu_le=timezone.now())
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': True})
    return redirect(request.META.get('HTTP_REFERER', 'notifs:admin_notifications'))

@login_required
@require_http_methods(['POST'])
def supprimer(request, pk):
    """Supprime une notification."""
    n = get_object_or_404(Notification, pk=pk)
    if not request.user.est_admin and n.destinataire != request.user:
        return JsonResponse({'error': 'Accès refusé'}, status=403)
    n.delete()
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': True, 'message': 'Notification supprimée'})
    return redirect(request.META.get('HTTP_REFERER', 'notifs:admin_notifications'))

@login_required
@require_http_methods(['POST'])
def envoyer(request):
    """Envoie une notification à un groupe d'utilisateurs (admin uniquement)."""
    if _admin_required(request):
        return JsonResponse({'error': 'Accès refusé'}, status=403)

    from apps.accounts.models import Utilisateur
    cible = request.POST.get('cible', 'tous')
    type_notification = request.POST.get('type_notification', 'SYSTEME')
    titre = request.POST.get('titre', '').strip()
    msg = request.POST.get('message', '').strip()

    if not titre or not msg:
        messages.error(request, 'Titre et message obligatoires.')
        return redirect(request.META.get('HTTP_REFERER', 'notifs:admin_notifications'))

    # Sélectionner les destinataires
    if cible == 'clients':
        users = Utilisateur.objects.filter(type_utilisateur='CLIENT', est_actif=True)
    elif cible == 'caissiers':
        users = Utilisateur.objects.filter(type_utilisateur='CAISSIER', est_actif=True)
    elif cible == 'gestionnaires':
        users = Utilisateur.objects.filter(type_utilisateur='GESTIONNAIRE_RESTAURANT', est_actif=True)
    else:
        users = Utilisateur.objects.filter(est_actif=True)

    notifs = [
        Notification(
            destinataire=u,
            type_notification=type_notification,
            priorite='MOYENNE',
            titre=titre,
            message=msg,
        )
        for u in users
    ]
    Notification.objects.bulk_create(notifs, batch_size=200)

    messages.success(request, f'{len(notifs)} notification(s) envoyée(s).')
    return redirect(request.META.get('HTTP_REFERER', 'notifs:admin_notifications'))


# ════════════════════════════════════════════════════════════════
# Vue client — mes notifications
# ════════════════════════════════════════════════════════════════
@login_required
def mes_notifications(request):
    qs = Notification.objects.filter(destinataire=request.user).order_by('-cree_le')
    non_lues = qs.filter(est_lu=False).count()

    paginator = Paginator(qs, 20)
    page_obj = paginator.get_page(request.GET.get('page', 1))

    return render(request, 'notifs/mes_notifications.html', {
        'notifs': page_obj,
        'page_obj': page_obj,
        'non_lues': non_lues,
        'notifications': qs[:5],
        'unread_notifications_count': non_lues,
    })


# ════════════════════════════════════════════════════════════════
# API JSON — pour le dropdown de la navbar
# ════════════════════════════════════════════════════════════════
@login_required
def api_notifs(request):
    """Retourne les 5 dernières notifs non lues en JSON."""
    notifs = Notification.objects.filter(
        destinataire=request.user, est_lu=False
    ).order_by('-cree_le')[:5]
    return JsonResponse({
        'count': Notification.objects.filter(destinataire=request.user, est_lu=False).count(),
        'notifs': [
            {
                'id': n.id,
                'titre': n.titre,
                'message': n.message[:80],
                'type': n.type_notification,
                'priorite': n.priorite,
                'cree_le': n.cree_le.isoformat(),
            }
            for n in notifs
        ],
    })


# ════════════════════════════════════════════════════════════════
# Utilitaire interne — créer une notif depuis une autre app
# ════════════════════════════════════════════════════════════════
def creer_notification(destinataire, titre, message, type_notification='SYSTEME',
                       priorite='MOYENNE', envoyer_email=False, lien='', texte_lien=''):
    """Crée une notification. Appeler depuis signals ou views externes."""
    try:
        n = Notification.objects.create(
            destinataire=destinataire,
            type_notification=type_notification,
            priorite=priorite,
            titre=titre,
            message=message,
            lien=lien,
            texte_lien=texte_lien,
            envoyer_email=envoyer_email,
        )
        if envoyer_email:
            n.envoyer_email_notification()
        return n
    except Exception as e:
        print(f'[notifs] Erreur création notif : {e}')
        return None


def _mes_notifs(request):
    try:
        return Notification.objects.filter(destinataire=request.user, est_lu=False).order_by('-cree_le')[:5]
    except Exception:
        return []