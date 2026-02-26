"""
Signaux pour la gestion des comptes utilisateurs
"""
import secrets
import string
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from django.utils import timezone

from .models import Utilisateur, ProfilUtilisateur


def generer_mot_de_passe(longueur=12):
    """Génère un mot de passe sécurisé"""
    alphabet = string.ascii_letters + string.digits + "!@#$%"
    # Garantir au moins 1 majuscule, 1 minuscule, 1 chiffre, 1 spécial
    mdp = [
        secrets.choice(string.ascii_uppercase),
        secrets.choice(string.ascii_lowercase),
        secrets.choice(string.digits),
        secrets.choice("!@#$%"),
    ]
    mdp += [secrets.choice(alphabet) for _ in range(longueur - 4)]
    secrets.SystemRandom().shuffle(mdp)
    return ''.join(mdp)


@receiver(post_save, sender=Utilisateur)
def creer_profil_utilisateur(sender, instance, created, **kwargs):
    """Créer automatiquement le profil lors de la création d'un utilisateur"""
    if created:
        ProfilUtilisateur.objects.get_or_create(utilisateur=instance)


@receiver(post_save, sender=Utilisateur)
def sauvegarder_profil_utilisateur(sender, instance, **kwargs):
    """Sauvegarder le profil utilisateur lors de la mise à jour"""
    if hasattr(instance, 'profil'):
        try:
            instance.profil.save()
        except Exception:
            pass

@receiver(post_save, sender=Utilisateur)
def envoyer_email_bienvenue(sender, instance, created, **kwargs):
    """
    Envoyer un email de bienvenue avec identifiants lors de la création du compte.
    Le mot de passe temporaire est généré et défini ici.
    """
    if not created or not instance.email:
        return

    # Vérifier si un mdp temporaire a été mis en session (transmis via signal)
    mot_de_passe = getattr(instance, '_mot_de_passe_temporaire', None)
    if not mot_de_passe:
        # Générer un nouveau mot de passe si non fourni
        mot_de_passe = generer_mot_de_passe()
        instance.set_password(mot_de_passe)
        # Sauvegarder sans déclencher le signal à nouveau
        Utilisateur.objects.filter(pk=instance.pk).update(
            password=instance.password
        )

    try:
        url_connexion = getattr(settings, 'SITE_URL', 'http://localhost:8000') + '/accounts/login/'

        # Contexte pour le template
        contexte = {
            'prenom': instance.prenom,
            'nom': instance.nom,
            'email': instance.email,
            'mot_de_passe': mot_de_passe,
            'type_utilisateur': instance.get_type_utilisateur_display(),
            'url_connexion': url_connexion,
            'annee': timezone.now().year,
        }

        # Rendu du template HTML
        html_content = render_to_string('emails/bienvenue.html', contexte)

        # Version texte simple
        text_content = f"""
Bonjour {instance.get_full_name()},

Votre compte MUTRALO/LONAB a été créé avec succès.

Identifiants de connexion :
  Email            : {instance.email}
  Mot de passe     : {mot_de_passe}
  Type de compte   : {instance.get_type_utilisateur_display()}

⚠️ Veuillez modifier votre mot de passe dès votre première connexion.

Lien de connexion : {url_connexion}

Cordialement,
L'équipe MUTRALO/LONAB
"""

        msg = EmailMultiAlternatives(
            subject="Bienvenue sur MUTRALO – Vos identifiants de connexion",
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[instance.email],
        )
        msg.attach_alternative(html_content, "text/html")
        msg.send(fail_silently=False)

    except Exception as erreur:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Erreur envoi email bienvenue pour {instance.email}: {erreur}")

def envoyer_email_avec_mdp(instance, mot_de_passe):
    """Fonction standalone pour envoyer l'email avec le mdp connu"""
    try:
        url_connexion = getattr(settings, 'SITE_URL', 'http://localhost:8000') + '/accounts/login/'
        contexte = {
            'prenom': instance.prenom,
            'nom': instance.nom,
            'email': instance.email,
            'mot_de_passe': mot_de_passe,
            'type_utilisateur': instance.get_type_utilisateur_display(),
            'url_connexion': url_connexion,
            'annee': timezone.now().year,
        }
        html_content = render_to_string('emails/bienvenue.html', contexte)
        text_content = (
            f"Bonjour {instance.get_full_name()},\n\n"
            f"Vos identifiants MUTRALO/LONAB :\n"
            f"  Email : {instance.email}\n"
            f"  Mot de passe : {mot_de_passe}\n\n"
            f"Connectez-vous sur : {url_connexion}\n\n"
            f"Modifiez votre mot de passe dès la première connexion.\n\n"
            f"L'équipe MUTRALO/LONAB"
        )
        msg = EmailMultiAlternatives(
            subject="Bienvenue sur MUTRALO – Vos identifiants de connexion",
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[instance.email],
        )
        msg.attach_alternative(html_content, "text/html")
        msg.send(fail_silently=False)
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Erreur email bienvenue {instance.email}: {e}")

