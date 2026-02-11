# 🎨 TEMPLATES LONAB - Guide Complet

## 📁 Structure des Templates

```
templates/
├── base.html                          # Template de base
├── auth/                              # Pages d'authentification
│   ├── login.html                     # Page de connexion
│   └── password_reset.html            # Réinitialisation mot de passe
├── dashboards/                        # Dashboards par rôle
│   ├── base_dashboard.html            # Template de base dashboard
│   ├── client_dashboard.html          # Dashboard CLIENT
│   ├── cashier_dashboard.html         # Dashboard CAISSIER
│   ├── restaurant_dashboard.html      # Dashboard RESTAURANT_MANAGER
│   └── admin_dashboard.html           # Dashboard SUPER_ADMIN
├── components/                        # Composants réutilisables
└── emails/                            # Templates d'emails
```

## 🎨 Couleurs LONAB

### Palette Principale
```css
--primary-green: #28a745    /* Vert principal */
--light-green: #C9FDD5      /* Vert clair (fond) */
--accent-red: #ff4d4d        /* Rouge accent */
```

### Variations
```css
--green-dark: #1e7e34       /* Vert foncé */
--green-hover: #218838      /* Vert hover */
--red-dark: #cc0000         /* Rouge foncé */
```

## 📄 Pages d'Authentification

### login.html
**URL:** `/auth/login/`

**Fonctionnalités:**
- Formulaire de connexion (email + mot de passe)
- Toggle affichage mot de passe
- "Se souvenir de moi"
- Lien mot de passe oublié
- Messages d'erreur/succès
- Design responsive

**Contexte requis:**
```python
{
    'messages': messages,  # Django messages
}
```

### password_reset.html
**URL:** `/auth/password-reset/`

**Fonctionnalités:**
- Formulaire de réinitialisation par email
- Lien retour connexion
- Messages de confirmation

## 🏠 Dashboards

### base_dashboard.html
Template de base incluant:
- **Sidebar** pliable avec menu de navigation
- **Navbar** avec recherche, notifications, profil
- **Zone de contenu** principale
- **Footer**
- JavaScript pour interactions

**Blocs disponibles:**
```django
{% block sidebar_menu %}{% endblock %}      # Menu sidebar
{% block page_content %}{% endblock %}      # Contenu principal
{% block dashboard_css %}{% endblock %}     # CSS additionnel
{% block dashboard_js %}{% endblock %}      # JS additionnel
```

### client_dashboard.html
**Pour:** Employés (CLIENT)

**Fonctionnalités:**
- Stats des tickets (disponibles, consommés)
- QR Code actif avec timer
- Actions rapides
- Historique d'activité

**Menu:**
- Tableau de bord
- Mes tickets
- Mon QR Code
- Historique
- Restaurants
- Menus
- Réservations

**Contexte requis:**
```python
{
    'available_tickets_count': int,
    'consumed_tickets_count': int,
    'total_value': Decimal,
    'active_reservations_count': int,
    'qr_code': QRCode or None,
    'recent_activity': QuerySet[ConsumptionLog],
}
```

### cashier_dashboard.html
**Pour:** Caissiers

**Fonctionnalités:**
- Stats ventes (jour, mois)
- Transactions récentes
- Actions rapides (vente, programmation)
- Restaurants actifs

**Menu:**
- Tableau de bord
- Vente de tickets
- Clients
- Restaurants
- Programmations
- Rapports
- Historique

**Contexte requis:**
```python
{
    'today_sales_count': int,
    'today_sales_amount': Decimal,
    'month_sales_count': int,
    'month_sales_amount': Decimal,
    'month_tickets_sold': int,
    'active_clients_count': int,
    'recent_transactions': QuerySet[TicketTransaction],
    'active_restaurants': QuerySet[Restaurant],
}
```

### restaurant_dashboard.html
**Pour:** Managers de restaurant

**Fonctionnalités:**
- Stats consommations
- Scanner QR Code
- Menus du jour
- Réservations en attente
- Consommations récentes

**Menu:**
- Tableau de bord
- Scanner QR Code
- Consommations
- Menus
- Réservations
- Agences
- Statistiques
- Historique

**Contexte requis:**
```python
{
    'today_consumptions': int,
    'month_consumptions': int,
    'pending_reservations': int,
    'agencies_count': int,
    'today_menus': QuerySet[Menu],
    'recent_consumptions': QuerySet[ConsumptionLog],
}
```

### admin_dashboard.html
**Pour:** Super administrateurs

**Fonctionnalités:**
- Vue d'ensemble complète
- Stats globales (employés, directions, agences, restaurants)
- Graphiques
- Transactions récentes
- Activité système

**Menu:**
- Tableau de bord
- Vue d'ensemble
- **Organisation:** Directions, Agences, Utilisateurs
- **Gestion:** Tickets, Transactions, Restaurants, Programmations
- **Rapports:** Rapports, Statistiques, Audit
- **Paramètres:** Système, Notifications

**Contexte requis:**
```python
{
    'total_employees': int,
    'new_employees_month': int,
    'total_directions': int,
    'active_directions': int,
    'total_agencies': int,
    'active_agencies': int,
    'total_restaurants': int,
    'active_restaurants': int,
    'month_tickets_sold': int,
    'month_tickets_consumed': int,
    'month_revenue': Decimal,
    'top_directions': list,
    'recent_transactions': QuerySet[TicketTransaction],
    'recent_activities': QuerySet[AuditLog],
}
```

## 🎯 Composants Réutilisables

### Cards de Stats
```html
<div class="card" style="border-left: 4px solid var(--primary-green);">
    <div style="display: flex; align-items: center; justify-content: space-between;">
        <div>
            <div style="color: var(--text-muted); font-size: 12px;">Titre</div>
            <div style="font-size: 28px; font-weight: 700;">Valeur</div>
        </div>
        <div style="width: 50px; height: 50px; background: var(--light-green); border-radius: 50%; display: flex; align-items: center; justify-content: center;">
            <i class="fas fa-icon" style="font-size: 22px; color: var(--primary-green);"></i>
        </div>
    </div>
</div>
```

### Badges de Statut
```html
<span class="badge badge-success">Actif</span>
<span class="badge badge-danger">Inactif</span>
<span class="badge badge-warning">En attente</span>
```

### Boutons
```html
<button class="btn btn-primary">
    <i class="fas fa-plus"></i> Action
</button>

<button class="btn btn-outline">
    <i class="fas fa-edit"></i> Modifier
</button>

<button class="btn btn-danger">
    <i class="fas fa-trash"></i> Supprimer
</button>
```

### Tables
```html
<table class="table">
    <thead>
        <tr>
            <th>Colonne 1</th>
            <th>Colonne 2</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td>Donnée 1</td>
            <td>Donnée 2</td>
        </tr>
    </tbody>
</table>
```

### Alertes
```html
<div class="alert alert-success">
    <i class="fas fa-check-circle"></i>
    Message de succès
</div>

<div class="alert alert-error">
    <i class="fas fa-exclamation-circle"></i>
    Message d'erreur
</div>
```

## 📱 Responsive Design

### Breakpoints
```css
@media (max-width: 768px)  /* Tablettes */
@media (max-width: 480px)  /* Mobiles */
```

### Comportements
- **Desktop:** Sidebar visible, navbar complète
- **Tablette:** Sidebar cachée (toggle), recherche réduite
- **Mobile:** Menu hamburger, sidebar overlay

## 🔧 JavaScript

### Fonctions Principales

**main.js:**
- `showSuccess(message)` - Afficher succès
- `showError(message)` - Afficher erreur
- `formatCurrency(amount)` - Formatter montant
- `formatDate(date)` - Formatter date
- `copyToClipboard(text)` - Copier texte
- `exportToCSV(data, filename)` - Export CSV

**dashboard.js:**
- `toggleSidebar()` - Plier/déplier sidebar
- `toggleDropdown(id)` - Toggle dropdown
- `sortTable(table, column)` - Trier table
- `filterTable(table, term)` - Filtrer table

## 🎨 CSS Personnalisé

### Variables Disponibles
```css
var(--primary-green)       /* Vert principal */
var(--light-green)         /* Vert clair */
var(--accent-red)          /* Rouge */
var(--text-primary)        /* Texte principal */
var(--text-secondary)      /* Texte secondaire */
var(--bg-primary)          /* Fond principal */
var(--border-color)        /* Bordure */
var(--spacing-md)          /* Espacement moyen */
```

## 📝 Conventions

### Nommage
- Classes: `kebab-case` (ex: `nav-link`)
- IDs: `camelCase` (ex: `globalSearch`)
- Variables CSS: `--kebab-case`

### Structure HTML
- Indentation: 4 espaces
- Fermeture balises: Toujours explicite
- Attributs: Guillemets doubles

### Commentaires
```html
<!-- ============================================
     Section Title
     ============================================ -->
```

## 🚀 Utilisation

### Créer une Nouvelle Page

1. Hériter du template approprié
```django
{% extends 'dashboards/base_dashboard.html' %}
```

2. Définir les blocs
```django
{% block title %}Mon Titre{% endblock %}
{% block page_content %}
    <!-- Contenu -->
{% endblock %}
```

3. Ajouter CSS/JS si nécessaire
```django
{% block dashboard_css %}
<style>
    /* CSS personnalisé */
</style>
{% endblock %}

{% block dashboard_js %}
<script>
    // JS personnalisé
</script>
{% endblock %}
```

## 📌 Notes Importantes

1. **Icons:** Utiliser Font Awesome 6.4.0
2. **Formulaires:** Toujours inclure `{% csrf_token %}`
3. **Messages:** Utiliser Django messages framework
4. **Responsive:** Tester sur mobile/tablette/desktop
5. **Performance:** Minimiser CSS/JS en production

## 🎯 Prochaines Étapes

- [ ] Créer composants réutilisables
- [ ] Ajouter templates d'emails
- [ ] Implémenter modals
- [ ] Ajouter tooltips
- [ ] Créer pages d'erreur (404, 500)

---

**Version:** 1.0  
**Date:** Février 2024  
**Design:** LONAB - MUTRALO