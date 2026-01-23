# stagiaire/models.py
from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator  # AJOUTEZ CET IMPORT
from UserApp.models import User
from stages.models import Stage

class Stagiaire(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    numero_carte_etudiant = models.CharField(max_length=20)
    universite = models.CharField(max_length=100)
    specialite = models.CharField(max_length=100, blank=True, null=True)
    stages = models.ManyToManyField(Stage, related_name="stagiaires")
    est_valide = models.BooleanField(default=False)
    date_validation = models.DateTimeField(null=True, blank=True)
    
    # AJOUTEZ CES CHAMPS POUR LE RATING (BIEN ALIGNÉS)
    rating = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(5)],
        verbose_name="Évaluation (0-5 étoiles)"
    )
    commentaire_evaluation = models.TextField(blank=True, null=True, verbose_name="Commentaire d'évaluation")
    date_evaluation = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"{self.user.first_name} {self.user.last_name}"
    
    def get_stars_html(self):
        """Génère le HTML pour afficher les étoiles"""
        full_stars = self.rating
        empty_stars = 5 - self.rating
        
        stars = '★' * full_stars + '☆' * empty_stars
        return f'<span class="stars" title="{self.rating}/5">{stars}</span>'