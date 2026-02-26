"""
Vues pour l'application restaurants — v3
Logique :
  - Menu = un plat individuel (nom, photo, quantité, prix, date spécifique)
  - Client voit les plats uniquement si date == aujourd'hui ET heure >= 08h00
  - Planning : une agence ne peut avoir qu'un restaurant actif simultanément
  - Gestionnaire bloqué si restaurant non programmé
"""
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib import messages
from django.db.models import Q, Count
from django.utils import timezone
from dateutil.relativedelta import relativedelta
from .models import Restaurant, PlanningRestaurant, Menu, Reservation

JOURS_MAP = {
    'Monday': 'LUNDI', 'Tuesday': 'MARDI', 'Wednesday': 'MERCREDI',
    'Thursday': 'JEUDI', 'Friday': 'VENDREDI',
    'Saturday': 'LUNDI', 'Sunday': 'LUNDI',
}

def _jour_fr():
    return JOURS_MAP.get(timezone.now().strftime('%A'), 'LUNDI')

def _debut_fin_mois(date=None):
    d = date or timezone.now().date()
    debut = d.replace(day=1)
    fin = debut + relativedelta(months=1) - relativedelta(days=1)
    return debut, fin

def _est_admin_ou_caissier(user):
    return user.est_admin or user.est_caissier

def _restaurant_a_planning_actif(restaurant):
    """Le restaurant a-t-il un planning actif aujourd'hui ?"""
    aujourd_hui = timezone.now().date()
    return PlanningRestaurant.objects.filter(
        restaurant=restaurant, est_actif=True,
        date_debut__lte=aujourd_hui, date_fin__gte=aujourd_hui,
    ).exists()

def _verifier_acces_gestionnaire(request, restaurant=None):
    """Redirige le gestionnaire si son restaurant n'est pas programmé."""
    if not request.user.est_gestionnaire_restaurant:
        return redirect('accounts:dashboard')
    r = restaurant or request.user.restaurant_gere
    if not r:
        messages.error(request, 'Aucun restaurant assigné à votre compte.')
        return redirect('accounts:dashboard')
    if not _restaurant_a_planning_actif(r):
        messages.warning(request, f'Le restaurant « {r.nom} » n\'est pas programmé actuellement. Contactez votre administrateur.')
        return redirect('accounts:dashboard')
    return None

# ════════════════════════════════════════════════════════════════
# ADMIN + CAISSIER — Restaurants
# ════════════════════════════════════════════════════════════════

@login_required
def restaurants_list(request):
    if not _est_admin_ou_caissier(request.user):
        messages.warning(request, 'Accès refusé.')
        return redirect('accounts:dashboard')
    qs = Restaurant.objects.annotate(
        nb_plannings=Count('plannings', filter=Q(plannings__est_actif=True)),
        nb_reservations=Count('reservations'),
    )
    if s := request.GET.get('statut'):
        qs = qs.filter(statut=s)
    if q := request.GET.get('search'):
        qs = qs.filter(Q(nom__icontains=q) | Q(code__icontains=q) | Q(ville__icontains=q))
    return render(request, 'restaurants/restaurants_list.html', {
        'restaurants': qs.order_by('nom'),
        'total': Restaurant.objects.count(),
        'actifs': Restaurant.objects.filter(statut='ACTIF').count(),
        'inactifs': Restaurant.objects.filter(statut='INACTIF').count(),
        'suspendus': Restaurant.objects.filter(statut='SUSPENDU').count(),
    })

@login_required
@require_http_methods(["POST"])
def restaurant_create(request):
    if not _est_admin_ou_caissier(request.user):
        return JsonResponse({'error': 'Permission refusée'}, status=403)
    try:
        code = request.POST.get('code', '').strip().upper()
        if not code:
            return JsonResponse({'error': 'Le code est obligatoire'}, status=400)
        if Restaurant.objects.filter(code=code).exists():
            return JsonResponse({'error': f'Code « {code} » déjà utilisé'}, status=400)
        r = Restaurant.objects.create(
            nom=request.POST.get('nom', '').strip(), code=code,
            description=request.POST.get('description', ''),
            adresse=request.POST.get('adresse', '').strip(),
            ville=request.POST.get('ville', '').strip(),
            telephone=request.POST.get('telephone', '').strip(),
            email=request.POST.get('email', '') or '',
            statut=request.POST.get('statut', 'ACTIF'),
        )
        if request.FILES.get('logo'):
            r.logo = request.FILES['logo']; r.save()
        return JsonResponse({'success': True, 'message': f'Restaurant {r.nom} créé', 'id': r.id})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

@login_required
def restaurant_edit(request, pk):
    if not _est_admin_ou_caissier(request.user):
        return JsonResponse({'error': 'Permission refusée'}, status=403)
    r = get_object_or_404(Restaurant, pk=pk)
    if request.method == 'GET':
        return JsonResponse({
            'id': r.id, 'nom': r.nom, 'code': r.code, 'description': r.description,
            'adresse': r.adresse, 'ville': r.ville, 'telephone': r.telephone,
            'email': r.email, 'statut': r.statut,
            'logo_url': r.logo.url if r.logo else '',
        })
    try:
        r.nom = request.POST.get('nom', r.nom)
        r.description = request.POST.get('description', r.description)
        r.adresse = request.POST.get('adresse', r.adresse)
        r.ville = request.POST.get('ville', r.ville)
        r.telephone = request.POST.get('telephone', r.telephone)
        r.email = request.POST.get('email', r.email) or ''
        r.statut = request.POST.get('statut', r.statut)
        if request.FILES.get('logo'): r.logo = request.FILES['logo']
        r.save()
        return JsonResponse({'success': True, 'message': f'Restaurant {r.nom} mis à jour'})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

@login_required
@require_http_methods(["POST"])
def restaurant_delete(request, pk):
    if not (request.user.est_admin or request.user.est_caissier):
        return JsonResponse({'error': 'Permission refusée'}, status=403)
    r = get_object_or_404(Restaurant, pk=pk)
    nom = r.nom; r.delete()
    return JsonResponse({'success': True, 'message': f'Restaurant {nom} supprimé'})

@login_required
def restaurant_detail(request, pk):
    r = get_object_or_404(Restaurant, pk=pk)
    aujourd_hui = timezone.now().date()
    debut_mois, _ = _debut_fin_mois(aujourd_hui)
    agences = list(
        PlanningRestaurant.objects.filter(restaurant=r, est_actif=True)
        .select_related('agence')
        .values('agence__nom', 'date_debut', 'date_fin', 'type_planning')
    )
    return JsonResponse({
        'id': r.id, 'nom': r.nom, 'code': r.code,
        'description': r.description, 'adresse': r.adresse,
        'ville': r.ville, 'telephone': r.telephone, 'email': r.email,
        'statut': r.statut, 'logo_url': r.logo.url if r.logo else '',
        'tickets_mois': r.tickets_consommes.filter(date_consommation__date__gte=debut_mois).count(),
        'nb_menus': r.menus.filter(est_disponible=True).count(),
        'nb_plannings_actifs': r.plannings.filter(est_actif=True).count(),
        'agences': agences,
    })

# ════════════════════════════════════════════════════════════════
# ADMIN + GESTIONNAIRE — Menus (= plats individuels)
# ════════════════════════════════════════════════════════════════

@login_required
def menus_list(request):
    if not (request.user.est_admin or request.user.est_gestionnaire_restaurant):
        return redirect('accounts:dashboard')
    # Gestionnaire : vérifier accès
    if request.user.est_gestionnaire_restaurant:
        redirect_r = _verifier_acces_gestionnaire(request)
        if redirect_r: return redirect_r

    qs = Menu.objects.select_related('restaurant')
    if request.user.est_gestionnaire_restaurant and request.user.restaurant_gere:
        qs = qs.filter(restaurant=request.user.restaurant_gere)
    if rid := request.GET.get('restaurant'):
        qs = qs.filter(restaurant_id=rid)
    if date_f := request.GET.get('date'):
        qs = qs.filter(date=date_f)
    if jour := request.GET.get('jour'):
        qs = qs.filter(jour_semaine=jour)

    # Groupement par date pour l'affichage gestionnaire
    from itertools import groupby
    menus_qs = list(qs.order_by('date', 'jour_semaine', 'id'))
    menus_par_date = {}
    for m in menus_qs:
        key = m.date.isoformat() if m.date else m.jour_semaine
        if key not in menus_par_date:
            menus_par_date[key] = {'label': m.date.strftime('%A %d %B %Y') if m.date else m.get_jour_semaine_display(), 'date': m.date, 'jour': m.jour_semaine, 'plats': []}
        menus_par_date[key]['plats'].append(m)

    return render(request, 'restaurants/menus_list.html', {
        'menus_par_date': menus_par_date,
        'menus': menus_qs,
        'restaurants': Restaurant.objects.filter(statut='ACTIF'),
        'jours': Menu.JOUR_CHOICES,
        'est_gestionnaire': request.user.est_gestionnaire_restaurant,
        'restaurant_gere': request.user.restaurant_gere if request.user.est_gestionnaire_restaurant else None,
    })

@login_required
@require_http_methods(["POST"])
def menu_create(request):
    if not (request.user.est_admin or request.user.est_gestionnaire_restaurant):
        return JsonResponse({'error': 'Permission refusée'}, status=403)
    try:
        rid = (request.user.restaurant_gere_id
               if request.user.est_gestionnaire_restaurant
               else request.POST.get('restaurant'))
        date_val = request.POST.get('date') or None
        jour_val = request.POST.get('jour_semaine') or 'LUNDI'
        # Si date fournie, déduire le jour de semaine automatiquement
        if date_val:
            import datetime
            d_obj = datetime.date.fromisoformat(date_val)
            jours_python = ['LUNDI','MARDI','MERCREDI','JEUDI','VENDREDI','LUNDI','LUNDI']
            jour_val = jours_python[d_obj.weekday()]

        m = Menu.objects.create(
            restaurant_id=rid,
            nom=request.POST.get('nom', '').strip(),
            description=request.POST.get('description', ''),
            plats='',  # Non utilisé — compatibilité modèle
            jour_semaine=jour_val,
            date=date_val,
            quantite_disponible=request.POST.get('quantite_disponible') or None,
            prix=request.POST.get('prix', 0),
            est_disponible=True,
        )
        if request.FILES.get('image'):
            m.image = request.FILES['image']; m.save()
        return JsonResponse({'success': True, 'message': f'Plat « {m.nom} » créé', 'id': m.id,
                             'nom': m.nom, 'date': m.date.isoformat() if m.date else '',
                             'quantite_disponible': m.quantite_disponible,
                             'image_url': m.image.url if m.image else ''})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

@login_required
def menu_edit(request, pk):
    m = get_object_or_404(Menu, pk=pk)
    if request.method == 'GET':
        return JsonResponse({
            'id': m.id, 'nom': m.nom, 'description': m.description,
            'jour_semaine': m.jour_semaine,
            'date': m.date.isoformat() if m.date else '',
            'quantite_disponible': m.quantite_disponible,
            'prix': str(m.prix), 'est_disponible': m.est_disponible,
            'restaurant_id': m.restaurant_id,
            'image_url': m.image.url if m.image else '',
        })
    try:
        m.nom = request.POST.get('nom', m.nom)
        m.description = request.POST.get('description', m.description)
        date_val = request.POST.get('date') or None
        if date_val:
            import datetime
            d_obj = datetime.date.fromisoformat(date_val)
            jours_python = ['LUNDI','MARDI','MERCREDI','JEUDI','VENDREDI','LUNDI','LUNDI']
            m.jour_semaine = jours_python[d_obj.weekday()]
            m.date = date_val
        m.quantite_disponible = request.POST.get('quantite_disponible') or m.quantite_disponible
        m.prix = request.POST.get('prix', m.prix)
        m.est_disponible = request.POST.get('est_disponible', '1') == '1'
        if request.FILES.get('image'): m.image = request.FILES['image']
        m.save()
        return JsonResponse({'success': True, 'message': f'Plat « {m.nom} » mis à jour'})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

@login_required
@require_http_methods(["POST"])
def menu_delete(request, pk):
    m = get_object_or_404(Menu, pk=pk)
    nom = m.nom; m.delete()
    return JsonResponse({'success': True, 'message': f'Plat « {nom} » supprimé'})

@login_required
@require_http_methods(["POST"])
@require_http_methods(["POST"])
def menu_duplicate(request):
    """Duplique tous les plats d'une date source vers une date cible."""
    if not (request.user.est_admin or request.user.est_gestionnaire_restaurant):
        return JsonResponse({'error': 'Permission refusée'}, status=403)
    try:
        import datetime
        date_source = request.POST.get('date_source', '').strip()
        date_cible  = request.POST.get('date_cible', '').strip()
        rid = (request.user.restaurant_gere_id
               if request.user.est_gestionnaire_restaurant
               else request.POST.get('restaurant'))

        if not date_source or not date_cible:
            return JsonResponse({'error': 'Dates source et cible obligatoires'}, status=400)
        if date_source == date_cible:
            return JsonResponse({'error': 'Les dates source et cible doivent être différentes'}, status=400)
        if not rid:
            return JsonResponse({'error': 'Restaurant non spécifié'}, status=400)

        plats_source = Menu.objects.filter(restaurant_id=rid, date=date_source)
        if not plats_source.exists():
            # Essai par jour_semaine si pas de date exacte
            plats_source = Menu.objects.filter(restaurant_id=rid, date__isnull=True,
                                               jour_semaine=JOURS_MAP.get(
                                                   datetime.date.fromisoformat(date_source).strftime('%A'), 'LUNDI'))
        if not plats_source.exists():
            return JsonResponse({'error': f'Aucun plat trouvé pour le {date_source}'}, status=400)

        # Déduire le jour de la date cible
        d_cible   = datetime.date.fromisoformat(date_cible)
        jours_py  = ['LUNDI', 'MARDI', 'MERCREDI', 'JEUDI', 'VENDREDI', 'SAMEDI', 'DIMANCHE']
        jour_cible = jours_py[d_cible.weekday()]

        # Supprimer les plats existants sur la date cible si demandé
        remplacer = request.POST.get('remplacer', '0') == '1'
        if remplacer:
            Menu.objects.filter(restaurant_id=rid, date=date_cible).delete()

        nb_crees = 0
        for plat in plats_source:
            fields = dict(
                restaurant_id=rid,
                nom=plat.nom,
                description=plat.description or '',
                jour_semaine=jour_cible,
                date=d_cible,
                quantite_disponible=plat.quantite_disponible,
                prix=plat.prix,
                est_disponible=True,
            )
            # Inclure plats seulement si le champ existe sur le modèle
            try:
                Menu._meta.get_field('plats')
                fields['plats'] = getattr(plat, 'plats', '') or ''
            except Exception:
                pass

            nouveau = Menu.objects.create(**fields)
            # Réutiliser la même image (même fichier stocké)
            if plat.image:
                nouveau.image = plat.image
                nouveau.save(update_fields=['image'])
            nb_crees += 1

        d_cible_fmt = d_cible.strftime('%d/%m/%Y')
        return JsonResponse({
            'success': True,
            'message': f'{nb_crees} plat{"s" if nb_crees > 1 else ""} dupliqué{"s" if nb_crees > 1 else ""} vers le {d_cible_fmt}',
            'nb': nb_crees,
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

@login_required
def menus_dates(request):
    """Retourne les dates ayant des plats pour ce restaurant (pour le datepicker)."""
    rid = None
    if request.user.est_gestionnaire_restaurant and request.user.restaurant_gere:
        rid = request.user.restaurant_gere_id
    else:
        rid = request.GET.get('restaurant')
    dates = list(Menu.objects.filter(restaurant_id=rid, date__isnull=False).values_list('date', flat=True).distinct().order_by('date'))
    return JsonResponse({'dates': [d.isoformat() for d in dates]})

# ════════════════════════════════════════════════════════════════
# ADMIN + CAISSIER — Plannings
# ════════════════════════════════════════════════════════════════

@login_required
def plannings_list(request):
    """Vue admin et caissier — liste des plannings."""
    if not _est_admin_ou_caissier(request.user):
        return redirect('accounts:dashboard')
    qs = PlanningRestaurant.objects.select_related('restaurant', 'agence', 'cree_par')
    # Caissier : ne voit que son agence
    if request.user.est_caissier and request.user.agence:
        qs = qs.filter(agence=request.user.agence)
    if rid := request.GET.get('restaurant'):
        qs = qs.filter(restaurant_id=rid)
    if a := request.GET.get('actif'):
        qs = qs.filter(est_actif=(a == '1'))
    from apps.accounts.models import Agence
    return render(request, 'restaurants/plannings_list.html', {
        'plannings': qs.order_by('-date_debut'),
        'restaurants': Restaurant.objects.filter(statut='ACTIF'),
        'agences': Agence.objects.filter(est_active=True),
        'est_caissier': request.user.est_caissier,
        'agence_caissier': request.user.agence if request.user.est_caissier else None,
    })

@login_required
@require_http_methods(["POST"])
def planning_create(request):
    if not _est_admin_ou_caissier(request.user):
        return JsonResponse({'error': 'Permission refusée'}, status=403)
    try:
        agence_id = (request.user.agence_id
                     if request.user.est_caissier
                     else request.POST.get('agence'))
        restaurant_id = request.POST.get('restaurant')
        date_debut = request.POST.get('date_debut')
        date_fin = request.POST.get('date_fin')

        # ── Règle : une seule agence peut accueillir un restaurant à la fois
        # Vérifier qu'il n'y a pas déjà un restaurant actif pour cette agence sur cette période
        chevauchement_agence = PlanningRestaurant.objects.filter(
            agence_id=agence_id, est_actif=True
        ).filter(
            Q(date_debut__lte=date_fin) & Q(date_fin__gte=date_debut)
        ).exclude(restaurant_id=restaurant_id)

        if chevauchement_agence.exists():
            autre = chevauchement_agence.first()
            return JsonResponse({
                'error': f'Cette agence a déjà « {autre.restaurant.nom} » programmé du {autre.date_debut.strftime("%d/%m/%Y")} au {autre.date_fin.strftime("%d/%m/%Y")}. Un seul restaurant par agence à la fois.'
            }, status=400)

        p = PlanningRestaurant.objects.create(
            restaurant_id=restaurant_id,
            agence_id=agence_id,
            type_planning=request.POST.get('type_planning', 'MENSUEL'),
            date_debut=date_debut,
            date_fin=date_fin,
            est_actif=True, cree_par=request.user,
        )
        return JsonResponse({'success': True, 'message': 'Planning créé avec succès', 'id': p.id})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

@login_required
def planning_edit(request, pk):
    p = get_object_or_404(PlanningRestaurant, pk=pk)
    if request.method == 'GET':
        return JsonResponse({
            'id': p.id, 'restaurant_id': p.restaurant_id, 'agence_id': p.agence_id,
            'type_planning': p.type_planning,
            'date_debut': p.date_debut.isoformat(),
            'date_fin': p.date_fin.isoformat(),
            'est_actif': p.est_actif,
        })
    try:
        if request.user.est_admin:
            p.agence_id = request.POST.get('agence', p.agence_id)
            p.restaurant_id = request.POST.get('restaurant', p.restaurant_id)
        p.type_planning = request.POST.get('type_planning', p.type_planning)
        p.date_debut = request.POST.get('date_debut', p.date_debut)
        p.date_fin = request.POST.get('date_fin', p.date_fin)
        p.est_actif = request.POST.get('est_actif') == '1'
        p.full_clean(); p.save()
        return JsonResponse({'success': True, 'message': 'Planning mis à jour'})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

@login_required
@require_http_methods(["POST"])
def planning_delete(request, pk):
    p = get_object_or_404(PlanningRestaurant, pk=pk)
    p.delete()
    return JsonResponse({'success': True, 'message': 'Planning supprimé'})

# ════════════════════════════════════════════════════════════════
# GESTIONNAIRE — Dashboard, Scanner, Consommations, Réservations, Agences
# ════════════════════════════════════════════════════════════════

@login_required
def gestionnaire_dashboard(request):
    redir = _verifier_acces_gestionnaire(request)
    if redir: return redir
    restaurant = request.user.restaurant_gere
    aujourd_hui = timezone.now().date()
    debut_semaine = aujourd_hui - timezone.timedelta(days=aujourd_hui.weekday())
    debut_mois, _ = _debut_fin_mois(aujourd_hui)
    reservations = Reservation.objects.filter(
        restaurant=restaurant, date_reservation=aujourd_hui
    ).select_related('client', 'menu').order_by('statut')

    # Données graphe 7 jours pour Chart.js
    graph_7j = []
    for i in range(6, -1, -1):
        j = aujourd_hui - timezone.timedelta(days=i)
        nb = restaurant.tickets_consommes.filter(date_consommation__date=j).count()
        graph_7j.append({'label': j.strftime('%a %d/%m'), 'value': nb})

    return render(request, 'restaurants/gestionnaire_dashboard.html', {
        'restaurant': restaurant,
        'menus_aujourd_hui': restaurant.menus.filter(date=aujourd_hui, est_disponible=True),
        'reservations_aujourd_hui': reservations,
        'tickets_aujourd_hui': restaurant.tickets_consommes.filter(
            date_consommation__date=aujourd_hui).count(),
        'tickets_semaine': restaurant.tickets_consommes.filter(
            date_consommation__date__gte=debut_semaine).count(),
        'tickets_ce_mois': restaurant.tickets_consommes.filter(
            date_consommation__date__gte=debut_mois).count(),
        'nb_attente': reservations.filter(statut='EN_ATTENTE').count(),
        'nb_confirme': reservations.filter(statut='CONFIRME').count(),
        'nb_termine': reservations.filter(statut='TERMINE').count(),
        'graph_7j': graph_7j,
        'aujourd_hui': aujourd_hui,
    })

@login_required
def gestionnaire_scanner(request):
    redir = _verifier_acces_gestionnaire(request)
    if redir: return redir
    restaurant = request.user.restaurant_gere
    aujourd_hui = timezone.now().date()
    derniers_scans = restaurant.tickets_consommes.filter(
        date_consommation__date=aujourd_hui
    ).select_related('proprietaire', 'proprietaire__agence').order_by('-date_consommation')[:15]
    return render(request, 'restaurants/gestionnaire_scanner.html', {
        'restaurant': restaurant,
        'derniers_scans': derniers_scans,
        'nb_scans_aujourd_hui': restaurant.tickets_consommes.filter(date_consommation__date=aujourd_hui).count(),
        'aujourd_hui': aujourd_hui,
    })

@login_required
def verifier_qr_code(request):
    redir = _verifier_acces_gestionnaire(request)
    if redir: return JsonResponse({'valide': False, 'error': 'Accès refusé'}, status=403)
    restaurant = request.user.restaurant_gere
    code = request.GET.get('code', '').strip()
    if not code:
        return JsonResponse({'valide': False, 'error': 'Code manquant'})
    try:
        from apps.tickets.models import CodeQR, Ticket
        qr = CodeQR.objects.select_related(
            'utilisateur', 'utilisateur__agence', 'utilisateur__direction'
        ).get(code=code)
        est_valide, message = qr.verifier_validite()
        if not est_valide:
            return JsonResponse({'valide': False, 'error': message})
        aujourd_hui = timezone.now().date()
        tickets_qs = Ticket.objects.filter(
            proprietaire=qr.utilisateur, statut='DISPONIBLE',
            valide_de__lte=aujourd_hui, valide_jusqua__gte=aujourd_hui,
        )
        ticket = tickets_qs.first()
        if not ticket:
            return JsonResponse({'valide': False, 'error': 'Aucun ticket valide disponible pour cet employé'})

        # ── Réservation du client pour aujourd'hui dans CE restaurant ──────
        reservation = Reservation.objects.filter(
            client=qr.utilisateur,
            restaurant=restaurant,
            date_reservation=aujourd_hui,
            statut__in=['EN_ATTENTE', 'CONFIRME'],
        ).select_related('menu').first()

        # ── Plats du jour dans CE restaurant (pour choix manuel) ──────────
        plats_du_jour = list(
            Menu.objects.filter(
                restaurant=restaurant,
                date=aujourd_hui,
                est_disponible=True,
            ).values('id', 'nom', 'quantite_disponible')
        )

        resp = {
            'valide': True, 'code': code,
            'client': qr.utilisateur.get_full_name(),
            'matricule': qr.utilisateur.matricule or '—',
            'agence': qr.utilisateur.agence.nom if qr.utilisateur.agence else '—',
            'ticket_numero': ticket.numero_ticket,
            'tickets_restants': tickets_qs.count(),
            'photo_url': qr.utilisateur.photo_profil.url if qr.utilisateur.photo_profil else '',
            'plats_du_jour': plats_du_jour,
            'plat_requis': True,   # ← le gestionnaire DOIT choisir un plat
            'reservation': None,
        }
        if reservation:
            resp['reservation'] = {
                'id': reservation.id,
                'menu_id': reservation.menu_id,
                'menu_nom': reservation.menu.nom,
                'statut': reservation.statut,
            }
        return JsonResponse(resp)
    except CodeQR.DoesNotExist:
        return JsonResponse({'valide': False, 'error': 'Code QR introuvable ou invalide'})
    except Exception as e:
        return JsonResponse({'valide': False, 'error': str(e)})

@login_required
@require_http_methods(["POST"])
def valider_qr_code(request):
    redir = _verifier_acces_gestionnaire(request)
    if redir: return JsonResponse({'error': 'Accès refusé'}, status=403)
    restaurant = request.user.restaurant_gere
    code = request.POST.get('code', '').strip()
    menu_id = request.POST.get('menu_id', '').strip()  # optionnel
    if not code:
        return JsonResponse({'error': 'Code QR manquant'}, status=400)
    try:
        from apps.tickets.models import CodeQR, Ticket
        qr = CodeQR.objects.get(code=code)
        est_valide, message = qr.verifier_validite()
        if not est_valide:
            return JsonResponse({'error': message, 'valide': False}, status=400)
        aujourd_hui = timezone.now().date()
        ticket = Ticket.objects.filter(
            proprietaire=qr.utilisateur, statut='DISPONIBLE',
            valide_de__lte=aujourd_hui, valide_jusqua__gte=aujourd_hui,
        ).first()
        if not ticket:
            return JsonResponse({'error': 'Aucun ticket valide disponible', 'valide': False}, status=400)

        # ── Traitement du plat consommé ────────────────────────────────────
        plat_consomme = None
        plat_nom = None

        # Cas 1 : le gestionnaire a transmis un menu_id explicite
        if menu_id:
            try:
                plat_consomme = Menu.objects.get(pk=menu_id, restaurant=restaurant)
                plat_nom = plat_consomme.nom
            except Menu.DoesNotExist:
                pass

        # Cas 2 : le client avait une réservation active → on l'utilise
        reservation_active = Reservation.objects.filter(
            client=qr.utilisateur, restaurant=restaurant,
            date_reservation=aujourd_hui,
            statut__in=['EN_ATTENTE', 'CONFIRME'],
        ).select_related('menu').first()

        if reservation_active:
            # Si pas de plat choisi manuellement → on utilise le plat réservé
            if not plat_consomme:
                plat_consomme = reservation_active.menu
                plat_nom = reservation_active.menu.nom
            # Marquer la réservation comme terminée
            reservation_active.statut = 'TERMINE'
            reservation_active.save(update_fields=['statut'])
        else:
            # Pas de réservation : le plat est OBLIGATOIRE si des plats du jour existent
            plats_disponibles = Menu.objects.filter(
                restaurant=restaurant, date=aujourd_hui, est_disponible=True
            ).exists()
            if plats_disponibles and not plat_consomme:
                return JsonResponse({
                    'error': 'Veuillez choisir un plat avant de valider',
                    'valide': False
                }, status=400)
            elif plat_consomme:
                # Créer une trace de réservation
                Reservation.objects.create(
                    client=qr.utilisateur,
                    restaurant=restaurant,
                    menu=plat_consomme,
                    date_reservation=aujourd_hui,
                    statut='TERMINE',
                )

        # Décrémenter quantité si applicable
        if plat_consomme and plat_consomme.quantite_disponible is not None:
            plat_consomme.quantite_disponible = max(0, plat_consomme.quantite_disponible - 1)
            if plat_consomme.quantite_disponible == 0:
                plat_consomme.est_disponible = False
            plat_consomme.save(update_fields=['quantite_disponible', 'est_disponible'])

        # ── Consommer le ticket ────────────────────────────────────────────
        ticket.marquer_comme_consomme(restaurant, request.user)
        qr.marquer_comme_utilise(restaurant)

        return JsonResponse({
            'valide': True,
            'message': f'Ticket validé — {qr.utilisateur.get_full_name()}',
            'client': qr.utilisateur.get_full_name(),
            'matricule': qr.utilisateur.matricule or '',
            'agence': qr.utilisateur.agence.nom if qr.utilisateur.agence else '',
            'ticket_numero': ticket.numero_ticket,
            'plat': plat_nom or '—',
        })
    except CodeQR.DoesNotExist:
        return JsonResponse({'error': 'Code QR invalide ou introuvable', 'valide': False}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e), 'valide': False}, status=400)

@login_required
def gestionnaire_consommations(request):
    redir = _verifier_acces_gestionnaire(request)
    if redir: return redir
    restaurant = request.user.restaurant_gere
    aujourd_hui = timezone.now().date()
    debut_mois, fin_mois = _debut_fin_mois(aujourd_hui)
    qs = restaurant.tickets_consommes.select_related('proprietaire', 'proprietaire__agence').order_by('-date_consommation')
    date_debut = request.GET.get('date_debut', '')
    date_fin_f = request.GET.get('date_fin', '')
    search = request.GET.get('search', '')
    agence_id = request.GET.get('agence', '')
    if date_debut: qs = qs.filter(date_consommation__date__gte=date_debut)
    if date_fin_f: qs = qs.filter(date_consommation__date__lte=date_fin_f)
    if search:
        qs = qs.filter(Q(numero_ticket__icontains=search)|Q(proprietaire__prenom__icontains=search)|Q(proprietaire__nom__icontains=search)|Q(proprietaire__matricule__icontains=search))
    if agence_id: qs = qs.filter(proprietaire__agence_id=agence_id)
    stats = {
        'total_filtre': qs.count(),
        'aujourd_hui': restaurant.tickets_consommes.filter(date_consommation__date=aujourd_hui).count(),
        'cette_semaine': restaurant.tickets_consommes.filter(date_consommation__date__gte=aujourd_hui-timezone.timedelta(days=6)).count(),
        'ce_mois': restaurant.tickets_consommes.filter(date_consommation__date__gte=debut_mois).count(),
    }
    graph_data = []
    for i in range(6, -1, -1):
        j = aujourd_hui - timezone.timedelta(days=i)
        nb = restaurant.tickets_consommes.filter(date_consommation__date=j).count()
        graph_data.append({'label': j.strftime('%a %d'), 'value': nb})
    from apps.accounts.models import Agence
    agences = Agence.objects.filter(plannings_restaurant__restaurant=restaurant).distinct()
    return render(request, 'restaurants/gestionnaire_consommations.html', {
        'restaurant': restaurant, 'tickets': qs[:300], 'stats': stats, 'agences': agences,
        'graph_data': graph_data, 'debut_mois': debut_mois, 'fin_mois': fin_mois, 'aujourd_hui': aujourd_hui,
        'filtres': {'search': search, 'date_debut': date_debut, 'date_fin': date_fin_f, 'agence': agence_id},
    })

@login_required
def gestionnaire_reservations(request):
    redir = _verifier_acces_gestionnaire(request)
    if redir: return redir
    restaurant = request.user.restaurant_gere
    aujourd_hui = timezone.now().date()
    date_filtre = request.GET.get('date', aujourd_hui.isoformat())
    qs = Reservation.objects.filter(restaurant=restaurant).select_related('client', 'client__agence', 'menu').order_by('statut', 'date_reservation')
    if date_filtre: qs = qs.filter(date_reservation=date_filtre)
    if statut := request.GET.get('statut'): qs = qs.filter(statut=statut)
    if search := request.GET.get('search'):
        qs = qs.filter(Q(client__prenom__icontains=search)|Q(client__nom__icontains=search)|Q(client__matricule__icontains=search))
    stats = {
        'en_attente': qs.filter(statut='EN_ATTENTE').count(),
        'confirme': qs.filter(statut='CONFIRME').count(),
        'termine': qs.filter(statut='TERMINE').count(),
        'annule': qs.filter(statut='ANNULE').count(),
    }
    return render(request, 'restaurants/gestionnaire_reservations.html', {
        'restaurant': restaurant, 'reservations': qs, 'stats': stats,
        'statuts': Reservation.STATUT_CHOICES, 'aujourd_hui': aujourd_hui,
        'date_filtre': date_filtre, 'filtre_statut': request.GET.get('statut', ''),
    })

@login_required
@require_http_methods(["POST"])
def gestionnaire_changer_statut_reservation(request, pk):
    redir = _verifier_acces_gestionnaire(request)
    if redir: return JsonResponse({'error': 'Accès refusé'}, status=403)
    r = get_object_or_404(Reservation, pk=pk, restaurant=request.user.restaurant_gere)
    action = request.POST.get('action')
    if action == 'confirmer' and r.statut == 'EN_ATTENTE':
        r.confirmer(); return JsonResponse({'success': True, 'message': 'Réservation confirmée', 'statut': 'CONFIRME'})
    elif action == 'terminer' and r.statut in ('EN_ATTENTE', 'CONFIRME'):
        r.terminer(); return JsonResponse({'success': True, 'message': 'Réservation terminée', 'statut': 'TERMINE'})
    elif action == 'annuler' and r.statut not in ('TERMINE', 'ANNULE'):
        r.annuler(); return JsonResponse({'success': True, 'message': 'Réservation annulée', 'statut': 'ANNULE'})
    return JsonResponse({'error': f'Action impossible sur ce statut'}, status=400)

@login_required
def gestionnaire_agences(request):
    redir = _verifier_acces_gestionnaire(request)
    if redir: return redir
    restaurant = request.user.restaurant_gere
    aujourd_hui = timezone.now().date()
    debut_mois, _ = _debut_fin_mois(aujourd_hui)
    plannings = PlanningRestaurant.objects.filter(restaurant=restaurant).select_related('agence', 'cree_par').order_by('-date_debut')
    agences_actives_ids = set(PlanningRestaurant.objects.filter(
        restaurant=restaurant, est_actif=True, date_debut__lte=aujourd_hui, date_fin__gte=aujourd_hui,
    ).values_list('agence_id', flat=True))
    from apps.accounts.models import Agence
    agences = Agence.objects.filter(plannings_restaurant__restaurant=restaurant).distinct().annotate(
        nb_tickets_mois=Count('employes__tickets', filter=Q(employes__tickets__restaurant_consommateur=restaurant, employes__tickets__date_consommation__date__gte=debut_mois, employes__tickets__statut='CONSOMME')),
        nb_tickets_total=Count('employes__tickets', filter=Q(employes__tickets__restaurant_consommateur=restaurant, employes__tickets__statut='CONSOMME')),
    )
    return render(request, 'restaurants/gestionnaire_agences.html', {
        'restaurant': restaurant, 'agences': agences, 'agences_actives_ids': agences_actives_ids,
        'plannings': plannings, 'aujourd_hui': aujourd_hui, 'debut_mois': debut_mois, 'nb_agences_actives': len(agences_actives_ids),
    })

# ════════════════════════════════════════════════════════════════
# CLIENT — Menus visibles (date == aujourd'hui ET heure >= 08:00)
# ════════════════════════════════════════════════════════════════

@login_required
def client_restaurants(request):
    if not request.user.est_client:
        return redirect('accounts:dashboard')
    aujourd_hui = timezone.now().date()
    plannings_actifs = []
    if request.user.agence:
        plannings_actifs = PlanningRestaurant.objects.filter(
            agence=request.user.agence, est_actif=True,
            date_debut__lte=aujourd_hui, date_fin__gte=aujourd_hui,
        ).select_related('restaurant')
    return render(request, 'restaurants/client_restaurants.html', {
        'restaurants_programmes': [p.restaurant for p in plannings_actifs],
        'plannings_actifs': plannings_actifs,
        'aujourd_hui': aujourd_hui, 'agence': request.user.agence,
    })

@login_required
def client_menus(request):
    if not request.user.est_client:
        return redirect('accounts:dashboard')
    maintenant = timezone.now()
    aujourd_hui = maintenant.date()
    heure_actuelle = maintenant.time()

    import datetime
    heure_ouverture = datetime.time(8, 0, 0)
    menus_disponibles = heure_actuelle >= heure_ouverture

    restaurants_actifs = []
    if request.user.agence:
        plannings = PlanningRestaurant.objects.filter(
            agence=request.user.agence, est_actif=True,
            date_debut__lte=aujourd_hui, date_fin__gte=aujourd_hui,
        ).select_related('restaurant')
        restaurants_actifs = [p.restaurant for p in plannings]

    # Menus = plats du jour uniquement (date == aujourd'hui)
    if menus_disponibles and restaurants_actifs:
        menus_du_jour = Menu.objects.filter(
            restaurant__in=restaurants_actifs,
            date=aujourd_hui,
            est_disponible=True,
        ).select_related('restaurant').order_by('restaurant__nom', 'nom')
    elif menus_disponibles:
        # Pas de restriction d'agence — afficher quand même
        menus_du_jour = Menu.objects.filter(date=aujourd_hui, est_disponible=True).select_related('restaurant')
    else:
        menus_du_jour = Menu.objects.none()

    tickets_valides = request.user.tickets.filter(
        statut='DISPONIBLE', valide_de__lte=aujourd_hui, valide_jusqua__gte=aujourd_hui
    ).count()

    # Mes réservations du jour
    mes_reservations = Reservation.objects.filter(
        client=request.user, date_reservation=aujourd_hui
    ).select_related('restaurant', 'menu')
    menus_deja_reserves = set(str(mid) for mid in mes_reservations.values_list('menu_id', flat=True))

    return render(request, 'restaurants/client_menus.html', {
        'menus_du_jour': menus_du_jour,
        'mes_reservations': mes_reservations,
        'menus_deja_reserves': menus_deja_reserves,
        'aujourd_hui': aujourd_hui,
        'menus_disponibles': menus_disponibles,
        'heure_ouverture': '08h00',
        'tickets_valides': tickets_valides,
        'restaurants_actifs': restaurants_actifs,
    })

@login_required
def client_reservations(request):
    if not request.user.est_client:
        return redirect('accounts:dashboard')
    qs = Reservation.objects.filter(client=request.user).select_related('restaurant', 'menu').order_by('-date_reservation')
    if statut := request.GET.get('statut'): qs = qs.filter(statut=statut)
    return render(request, 'restaurants/client_reservations.html', {
        'reservations': qs, 'statuts': Reservation.STATUT_CHOICES, 'filtre_actif': request.GET.get('statut', ''),
    })

@login_required
@require_http_methods(["POST"])
def client_reserver(request):
    if not request.user.est_client:
        return JsonResponse({'error': 'Permission refusée'}, status=403)
    try:
        menu_id = request.POST.get('menu_id')
        if not menu_id:
            return JsonResponse({'error': 'ID menu manquant'}, status=400)
        menu = get_object_or_404(Menu, pk=menu_id)
        aujourd_hui = timezone.now().date()
        date_r = request.POST.get('date_reservation', aujourd_hui.isoformat())

        # Vérifier ticket valide
        ticket_valide = request.user.tickets.filter(
            statut='DISPONIBLE', valide_de__lte=aujourd_hui, valide_jusqua__gte=aujourd_hui
        ).exists()
        if not ticket_valide:
            return JsonResponse({'error': 'Vous n\'avez aucun ticket valide ce mois-ci'}, status=400)

        # Vérifier pas déjà réservé ce menu aujourd'hui
        deja = Reservation.objects.filter(client=request.user, menu=menu, date_reservation=date_r).exists()
        if deja:
            return JsonResponse({'error': 'Vous avez déjà réservé ce plat aujourd\'hui'}, status=400)

        # Vérifier disponibilité
        if not menu.est_disponible:
            return JsonResponse({'error': 'Ce plat n\'est plus disponible'}, status=400)

        r = Reservation.objects.create(
            client=request.user,
            menu=menu,
            restaurant=menu.restaurant,
            date_reservation=date_r,
            statut='EN_ATTENTE',
        )
        return JsonResponse({'success': True, 'message': f'✓ Réservation confirmée — {menu.nom}', 'id': r.id})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

@login_required
@require_http_methods(["POST"])
def client_annuler_reservation(request, pk):
    r = get_object_or_404(Reservation, pk=pk, client=request.user)
    if r.statut == 'TERMINE':
        return JsonResponse({'error': 'Impossible d\'annuler une réservation terminée'}, status=400)
    r.statut = 'ANNULE'; r.save()
    return JsonResponse({'success': True, 'message': 'Réservation annulée'})

# ════════════════════════════════════════════════════════════════
# CAISSIER — Planifier un restaurant
# ════════════════════════════════════════════════════════════════

@login_required
def caissier_planifier_restaurant(request):
    if not _est_admin_ou_caissier(request.user):
        return redirect('accounts:dashboard')
    from apps.accounts.models import Agence
    agence_caissier = request.user.agence if request.user.est_caissier else None

    # Planning actif actuel pour l'agence du caissier
    planning_actif_actuel = None
    if agence_caissier:
        aujourd_hui = timezone.now().date()
        planning_actif_actuel = PlanningRestaurant.objects.filter(
            agence=agence_caissier, est_actif=True,
            date_debut__lte=aujourd_hui, date_fin__gte=aujourd_hui,
        ).select_related('restaurant').first()

    return render(request, 'restaurants/caissier_planifier.html', {
        'restaurants': Restaurant.objects.filter(statut='ACTIF'),
        'agences': Agence.objects.filter(est_active=True),
        'plannings_recents': PlanningRestaurant.objects.filter(
            **({'agence': agence_caissier} if agence_caissier else {})
        ).select_related('restaurant', 'agence').order_by('-date_creation')[:20],
        'est_caissier': request.user.est_caissier,
        'agence_caissier': agence_caissier,
        'planning_actif_actuel': planning_actif_actuel,
    })

@login_required
def caissier_restaurants(request):
    """Liste des restaurants de la VILLE de l'agence du caissier."""
    if not _est_admin_ou_caissier(request.user):
        return redirect('accounts:dashboard')

    agence = request.user.agence if request.user.est_caissier else None
    aujourd_hui = timezone.now().date()

    planning_actif = None
    if agence:
        planning_actif = PlanningRestaurant.objects.filter(
            agence=agence, est_actif=True,
            date_debut__lte=aujourd_hui, date_fin__gte=aujourd_hui,
        ).select_related('restaurant').first()

    # Filtrer uniquement les restaurants de la ville de l'agence
    ville_agence = agence.ville if agence else None
    base_qs = Restaurant.objects.filter(ville__iexact=ville_agence) if ville_agence else Restaurant.objects.all()
    qs = base_qs

    if search := request.GET.get('search'):
        qs = qs.filter(Q(nom__icontains=search) | Q(code__icontains=search))
    if statut := request.GET.get('statut'):
        qs = qs.filter(statut=statut)

    return render(request, 'restaurants/caissier_restaurants.html', {
        'restaurants':        qs.order_by('nom'),
        'total_restaurants':  base_qs.count(),
        'restaurants_actifs': base_qs.filter(statut='ACTIF').count(),
        'agence':             agence,
        'planning_actif':     planning_actif,
    })

