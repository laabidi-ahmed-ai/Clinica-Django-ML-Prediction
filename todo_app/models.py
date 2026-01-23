from django.db import models

# Create your models here.
# todo_app/models.py
from django.db import models
from UserApp.models import User

class TodoItem(models.Model):
    STATUS_CHOICES = [
        ('todo', 'À faire'),
        ('in_progress', 'En cours'),
        ('done', 'Terminé'),
    ]
    
    stagiaire = models.ForeignKey(
        User, 
        on_delete=models.CASCADE,
        related_name='todos'  # ← IMPORTANT: ajoutez related_name
    )
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='todo')
    priority = models.CharField(max_length=20, choices=[
        ('low', 'Basse'),
        ('medium', 'Moyenne'),
        ('high', 'Haute')
    ], default='medium')
    due_date = models.DateField(null=True, blank=True)
    fait = models.BooleanField(default=False)  # Gardez-le si vous l'utilisez
    
    def __str__(self):
        return self.title