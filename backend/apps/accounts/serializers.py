"""
Serializers pour l'application comptes
"""
from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from .models import Utilisateur, Direction, Agence, ProfilUtilisateur


class UtilisateurSerializer(serializers.ModelSerializer):
    """Serializer pour le modèle Utilisateur"""

    nom_complet = serializers.SerializerMethodField()
    direction_nom = serializers.CharField(source='direction.nom', read_only=True)
    agence_nom = serializers.CharField(source='agence.nom', read_only=True)
    superieur_nom = serializers.CharField(source='superieur_hierarchique.get_full_name', read_only=True)

    class Meta:
        model = Utilisateur
        fields = [
            'id', 'email', 'nom_utilisateur', 'prenom', 'nom', 'nom_complet',
            'telephone', 'genre', 'date_naissance', 'type_utilisateur',
            'matricule', 'departement', 'poste',
            'direction', 'direction_nom', 'agence', 'agence_nom',
            'superieur_hierarchique', 'superieur_nom',
            'restaurant_gere', 'photo_profil', 'adresse',
            'est_actif', 'est_verifie', 'date_inscription', 'derniere_connexion'
        ]
        read_only_fields = ['id', 'date_inscription', 'derniere_connexion', 'nom_complet']
        extra_kwargs = {
            'mot_de_passe': {'write_only': True},
        }

    def get_nom_complet(self, obj):
        return obj.get_full_name()


class UtilisateurCreateSerializer(serializers.ModelSerializer):
    """Serializer pour créer des utilisateurs"""

    mot_de_passe = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    mot_de_passe2 = serializers.CharField(write_only=True, required=True, label="Confirmer le mot de passe")

    class Meta:
        model = Utilisateur
        fields = [
            'email', 'mot_de_passe', 'mot_de_passe2', 'prenom', 'nom',
            'telephone', 'type_utilisateur', 'matricule', 'departement',
            'poste', 'direction', 'agence', 'superieur_hierarchique'
        ]

    def validate(self, attrs):
        if attrs['mot_de_passe'] != attrs['mot_de_passe2']:
            raise serializers.ValidationError({"mot_de_passe": "Les mots de passe ne correspondent pas."})
        return attrs

    def create(self, validated_data):
        validated_data.pop('mot_de_passe2')
        mot_de_passe = validated_data.pop('mot_de_passe')
        utilisateur = Utilisateur.objects.creer_utilisateur(mot_de_passe=mot_de_passe, **validated_data)
        return utilisateur


class LoginSerializer(serializers.Serializer):
    """Serializer pour la connexion"""

    email = serializers.EmailField(required=True)
    mot_de_passe = serializers.CharField(required=True, write_only=True, style={'input_type': 'password'})
    se_souvenir_de_moi = serializers.BooleanField(required=False, default=False)

    def validate(self, attrs):
        email = attrs.get('email')
        mot_de_passe = attrs.get('mot_de_passe')

        if email and mot_de_passe:
            utilisateur = authenticate(
                request=self.context.get('request'),
                email=email,
                password=mot_de_passe
            )

            if not utilisateur:
                raise serializers.ValidationError(
                    'Email ou mot de passe incorrect.',
                    code='authorization'
                )

            if not utilisateur.est_actif:
                raise serializers.ValidationError(
                    'Ce compte est désactivé.',
                    code='authorization'
                )
        else:
            raise serializers.ValidationError(
                'Email et mot de passe requis.',
                code='authorization'
            )

        attrs['utilisateur'] = utilisateur
        return attrs


class ReinitialisationMotDePasseSerializer(serializers.Serializer):
    """Serializer pour la demande de réinitialisation de mot de passe"""

    email = serializers.EmailField(required=True)

    def validate_email(self, value):
        if not Utilisateur.objects.filter(email=value).exists():
            raise serializers.ValidationError("Aucun utilisateur avec cet email.")
        return value


class ReinitialisationMotDePasseConfirmerSerializer(serializers.Serializer):
    """Serializer pour la confirmation de réinitialisation de mot de passe"""

    token = serializers.CharField(required=True)
    mot_de_passe = serializers.CharField(required=True, write_only=True, validators=[validate_password])
    mot_de_passe2 = serializers.CharField(required=True, write_only=True, label="Confirmer le mot de passe")

    def validate(self, attrs):
        if attrs['mot_de_passe'] != attrs['mot_de_passe2']:
            raise serializers.ValidationError({"mot_de_passe": "Les mots de passe ne correspondent pas."})
        return attrs


class DirectionSerializer(serializers.ModelSerializer):
    """Serializer pour le modèle Direction"""

    directeur_nom = serializers.CharField(source='directeur.get_full_name', read_only=True)
    total_employes = serializers.IntegerField(read_only=True)
    employes_actifs = serializers.IntegerField(read_only=True)

    class Meta:
        model = Direction
        fields = [
            'id', 'nom', 'code', 'description',
            'telephone', 'email', 'directeur', 'directeur_nom',
            'est_active', 'total_employes', 'employes_actifs',
            'date_creation', 'date_modification'
        ]
        read_only_fields = ['id', 'date_creation', 'date_modification']


class AgenceSerializer(serializers.ModelSerializer):
    """Serializer pour le modèle Agence"""

    direction_nom = serializers.CharField(source='direction.nom', read_only=True)
    responsable_nom = serializers.CharField(source='responsable.get_full_name', read_only=True)
    agence_parente_nom = serializers.CharField(source='agence_parente.nom', read_only=True)
    total_employes = serializers.IntegerField(read_only=True)
    employes_actifs = serializers.IntegerField(read_only=True)
    adresse_complete = serializers.CharField(read_only=True)

    class Meta:
        model = Agence
        fields = [
            'id', 'nom', 'code', 'type_agence',
            'adresse', 'adresse_complete', 'ville', 'region',
            'telephone', 'email',
            'direction', 'direction_nom',
            'agence_parente', 'agence_parente_nom',
            'responsable', 'responsable_nom',
             'total_employes', 'employes_actifs', 'a_capacite',
            'est_active', 'date_ouverture', 'date_fermeture',
            'date_creation', 'date_modification'
        ]
        read_only_fields = ['id', 'date_creation', 'date_modification']


class ProfilUtilisateurSerializer(serializers.ModelSerializer):
    """Serializer pour le modèle ProfilUtilisateur"""

    utilisateur_email = serializers.EmailField(source='utilisateur.email', read_only=True)
    utilisateur_nom = serializers.CharField(source='utilisateur.get_full_name', read_only=True)

    class Meta:
        model = ProfilUtilisateur
        fields = [
            'id', 'utilisateur', 'utilisateur_email', 'utilisateur_nom',
            'notification_email', 'notification_sms', 'langue',
            'contact_urgence_nom', 'contact_urgence_telephone',
            'notes', 'date_creation', 'date_modification'
        ]
        read_only_fields = ['id', 'utilisateur', 'date_creation', 'date_modification']


class ChangerMotDePasseSerializer(serializers.Serializer):
    """Serializer pour changer le mot de passe"""

    ancien_mot_de_passe = serializers.CharField(required=True, write_only=True)
    nouveau_mot_de_passe = serializers.CharField(required=True, write_only=True, validators=[validate_password])
    nouveau_mot_de_passe2 = serializers.CharField(required=True, write_only=True)

    def validate_ancien_mot_de_passe(self, value):
        utilisateur = self.context['request'].user
        if not utilisateur.check_password(value):
            raise serializers.ValidationError("Ancien mot de passe incorrect.")
        return value

    def validate(self, attrs):
        if attrs['nouveau_mot_de_passe'] != attrs['nouveau_mot_de_passe2']:
            raise serializers.ValidationError({"nouveau_mot_de_passe": "Les nouveaux mots de passe ne correspondent pas."})
        return attrs

    def save(self, **kwargs):
        utilisateur = self.context['request'].user
        utilisateur.set_password(self.validated_data['nouveau_mot_de_passe'])
        utilisateur.save()
        return utilisateur


class UtilisateurMiseAJourSerializer(serializers.ModelSerializer):
    """Serializer pour mettre à jour les informations de l'utilisateur"""

    class Meta:
        model = Utilisateur
        fields = [
            'prenom', 'nom', 'telephone', 'genre', 'date_naissance',
            'photo_profil', 'adresse', 'departement', 'poste',
            'direction', 'agence', 'superieur_hierarchique'
        ]

    def update(self, instance, validated_data):
        # Mise à jour des champs autorisés
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance


class ProfilUtilisateurMiseAJourSerializer(serializers.ModelSerializer):
    """Serializer pour mettre à jour le profil utilisateur"""

    class Meta:
        model = ProfilUtilisateur
        fields = [
            'notification_email', 'notification_sms', 'langue',
            'contact_urgence_nom', 'contact_urgence_telephone',
            'notes'
        ]

    def update(self, instance, validated_data):
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance