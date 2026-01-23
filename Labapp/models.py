from django.db import models
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.conf import settings  # To reference custom user model
from UserApp.models import User
# adapte l'import selon ton projet
# Use settings.AUTH_USER_MODEL for all user relations to support custom user model
from achatapp.models import Produit

# ----------------------------


# ----------------------------
# Abstract Laboratoire
# ----------------------------
class Laboratoire(models.Model):
    """
    Classe abstraite : contient les champs communs aux sous-classes (Recherche, Analyse).
    """
    nom = models.CharField(max_length=150)
    description = models.TextField(blank=True, null=True)
    localisation = models.CharField(max_length=150, blank=True, null=True)
    date_creation = models.DateField(blank=True, null=True)
    statut = models.CharField(
        max_length=20,
        choices=[('actif', 'Actif'), ('ferme', 'Fermé')],
        default='actif'
    )
    resultat = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

    def __str__(self):
        return self.nom


# ----------------------------
# Recherche Model
# ----------------------------
class Recherche(Laboratoire):
    nom_recherche = models.CharField(max_length=150)  # nom spécifique de la recherche
    maladie = models.CharField(max_length=150)
    objectif = models.TextField()
    date_deb = models.DateField()
    date_fin = models.DateField(blank=True, null=True)
    risque = models.CharField(max_length=50, blank=True, null=True)

    TYPE_RECHERCHE = [
        ('clinique', 'Clinique'),
        ('fondamentale', 'Fondamentale'),
        ('appliquee', 'Appliquée'),
    ]
    type_recherche = models.CharField(max_length=20, choices=TYPE_RECHERCHE, default='fondamentale')

    budget = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)], blank=True, null=True)

    ETAT_RECHERCHE = [
        ('en_cours', 'En cours'),
        ('terminee', 'Terminée'),
        ('suspendue', 'Suspendue'),
    ]
    etat = models.CharField(max_length=20, choices=ETAT_RECHERCHE, default='en_cours')

    publication_associee = models.URLField(blank=True, null=True)
    resultats_obtenus = models.TextField(blank=True, null=True)

    # Equipement and responsable with unique related_name
    equipement = models.ForeignKey(
        Produit, on_delete=models.SET_NULL, null=True, blank=True, related_name="recherches"
    )
    responsable = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="recherches_diriges"
    )

    def clean(self):
        if self.date_fin and self.date_fin < self.date_deb:
            raise ValidationError({"date_fin": "La date de fin doit être postérieure à la date de début."})

    def __str__(self):
        return f"{self.nom_recherche} ({self.maladie})"


# ----------------------------
# Analyse Model
# ----------------------------
class Analyse(Laboratoire):
    TYPE_ANALYSE = [
        ('biochimie', 'Biochimie'),
        ('immunologie', 'Immunologie'),
        ('genetique', 'Génétique'),
        ('microbio', 'Microbiologie'),
        ('autre', 'Autre'),
    ]
    type = models.CharField(max_length=30, choices=TYPE_ANALYSE, default='autre')
    category = models.CharField(max_length=100, blank=True, null=True)

    echantillon_code = models.CharField(max_length=50, unique=True)
    patient_id = models.CharField(max_length=50, blank=True, null=True)
    technique_utilisee = models.CharField(max_length=100, blank=True, null=True)

    date_prelevement = models.DateField()
    date_res = models.DateField(blank=True, null=True)

    ETAT_ANALYSE = [
        ('en_cours', 'En cours'),
        ('terminee', 'Terminée'),
        ('annulee', 'Annulée'),
    ]
    etat = models.CharField(max_length=20, choices=ETAT_ANALYSE, default='en_cours')

    cout = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)], blank=True, null=True)
    commentaire = models.TextField(blank=True, null=True)

    # Equipement and responsable with unique related_name
    equipement = models.ForeignKey(
        Produit, on_delete=models.SET_NULL, null=True, blank=True, related_name="analyses"
    )
    responsable = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="analyses_diriges"
    )
    responsable_analyse = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="analyses_responsable"
    )
    valide_par = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="analyses_validees"
    )

    def clean(self):
        if self.date_res and self.date_res < self.date_prelevement:
            raise ValidationError({"date_res": "La date du résultat doit être postérieure à la date de prélèvement."})

    def __str__(self):
        return f"Analyse {self.echantillon_code} - {self.get_type_display()}"
class BilanMedical(models.Model):
    # Reference the configured user model
    patient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    analyse = models.ForeignKey(Analyse, on_delete=models.CASCADE)
    date_created = models.DateTimeField(auto_now_add=True)
    pdf_file = models.FileField(upload_to='bilans_medical/', null=True, blank=True)

    def __str__(self):
        return f"Bilan: {self.patient.username} - {self.analyse.nom_analyse}"
class ChatRoom(models.Model):
    name = models.CharField(max_length=255)
    participants = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='chat_rooms')
    is_private = models.BooleanField(default=False)
    created_at = models.DateTimeField(null=True, blank=True)  # initially nullable

    def __str__(self):
        return self.name


class Message(models.Model):
    room = models.ForeignKey(ChatRoom, related_name='messages', on_delete=models.CASCADE)
    sender = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
