"""
Signaux pour la gestion des comptes utilisateurs
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import send_mail
from django.conf import settings

from .models import Utilisateur, ProfilUtilisateur


@receiver(post_save, sender=Utilisateur)
def creer_profil_utilisateur(sender, instance, created, **kwargs):
    """Créer automatiquement le profil lors de la création d'un utilisateur"""
    if created:
        ProfilUtilisateur.objects.create(utilisateur=instance)


@receiver(post_save, sender=Utilisateur)
def sauvegarder_profil_utilisateur(sender, instance, **kwargs):
    """Sauvegarder le profil utilisateur lors de la mise à jour"""
    if hasattr(instance, 'profil'):
        instance.profil.save()


@receiver(post_save, sender=Utilisateur)
def envoyer_email_bienvenue(sender, instance, created, **kwargs):
    """Envoyer un email de bienvenue lors de la création du compte"""
    if created and instance.email:
        sujet = f"Bienvenue sur LONAB – MUTRALO"

        message = f"""
Bonjour {instance.get_full_name()},

Votre compte a été créé avec succès sur la plateforme de gestion
des tickets de restauration.

Type de compte : {instance.get_type_utilisateur_display()}
Email : {instance.email}

Vous pouvez dès à présent vous connecter à votre espace personnel.

Cordialement,
L'équipe MUTRALO
"""

        try:
            send_mail(
                sujet,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [instance.email],
                fail_silently=True,
            )
        except Exception as erreur:
            print(f"Erreur lors de l'envoi de l'email : {erreur}")

