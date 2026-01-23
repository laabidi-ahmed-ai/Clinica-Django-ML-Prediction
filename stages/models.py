from django.db import models

from UserApp.models import User

class Stage(models.Model):
    TYPE_STAGE = [
        ('observation', 'Stage d\'Observation'),
        ('clinique', 'Stage Clinique'),
        ('chirurgical', 'Stage Chirurgical'),
        ('urgence', 'Stage aux Urgences'),
        ('specialise', 'Stage Spécialisé'),
        ('recherche', 'Stage de Recherche'),
        ('infirmier', 'Stage Infirmier'),
    ]
    
    SERVICE_CLINIQUE = [
        ('consultation', 'Consultation Externe'),
        ('hospitalisation', 'Hospitalisation'),
        ('urgence', 'Urgences'),
        ('chirurgie', 'Bloc Chirurgical'),
        ('maternite', 'Maternité'),
        ('pediatrie', 'Pédiatrie'),
        ('cardiologie', 'Cardiologie'),
        ('radiologie', 'Radiologie'),
        ('laboratoire', 'Laboratoire d\'Analyses'),
        ('pharmacie', 'Pharmacie'),
        ('administration', 'Administration'),
    ]
    
    STATUT_STAGE = [
        ('propose', 'Proposé'),
        ('valide', 'Validé'),
        ('en_cours', 'En Cours'),
        ('termine', 'Terminé'),
        ('annule', 'Annulé'),
        ('interrompu', 'Interrompu'),
    ]
    
    # Informations générales du stage
    intitule = models.CharField(max_length=200)
    description = models.TextField()
    objectifs = models.TextField(blank=True)  # Objectifs pédagogiques
    type_stage = models.CharField(max_length=20, choices=TYPE_STAGE)
    service = models.CharField(max_length=50, choices=SERVICE_CLINIQUE)
    
    # Dates et durée
    date_debut = models.DateField()
    date_fin = models.DateField()
    duree_semaines = models.PositiveIntegerField()  # Durée en semaines
    horaires_travail = models.CharField(max_length=100, blank=True)  # Ex: "8h-16h"
    
    # Statut et évaluation
    statut = models.CharField(max_length=20, choices=STATUT_STAGE, default='propose')
    note_finale = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)
    appreciation = models.TextField(blank=True)  # Commentaire de l'encadrant
    rapport_stage = models.FileField(upload_to='rapports_stage/', blank=True, null=True)
    
    # Relations - RENDU NON OBLIGATOIRE
    
    encadrant = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, 
                                 limit_choices_to={'role': 'Dr'})
   
    # Équipement et accès
    acces_logiciel_medical = models.BooleanField(default=False)
    badge_acces = models.CharField(max_length=20, blank=True)  # Numéro de badge
    vestiaire_attribue = models.CharField(max_length=10, blank=True)  # Numéro de vestiaire
    
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-date_debut']
        verbose_name = "Stage Médical"
        verbose_name_plural = "Stages Médicaux"
    
    def __str__(self):
        # Gérer le cas où le stagiaire est None
        if self.stagiaire:
            return f"{self.intitule} - {self.stagiaire.prenom} {self.stagiaire.nom}"
        else:
            return f"{self.intitule} - (Aucun stagiaire assigné)"
    
    def est_en_cours(self):
        from django.utils import timezone
        today = timezone.now().date()
        return self.date_debut <= today <= self.date_fin
    
    def pourcentage_realisation(self):
        from django.utils import timezone
        today = timezone.now().date()
        if today < self.date_debut:
            return 0
        elif today > self.date_fin:
            return 100
        else:
            total_days = (self.date_fin - self.date_debut).days
            days_passed = (today - self.date_debut).days
            return (days_passed / total_days) * 100