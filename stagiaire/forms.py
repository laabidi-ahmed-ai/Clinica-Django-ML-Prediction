# stagiaire/forms.py
from django import forms
from .models import Stagiaire

class PublicStagiaireForm(forms.ModelForm):
    class Meta:
        model = Stagiaire
        fields = ['numero_carte_etudiant', 'universite', 'specialite']
        widgets = {
            'numero_carte_etudiant': forms.TextInput(attrs={'class': 'form-control'}),
            'universite': forms.TextInput(attrs={'class': 'form-control'}),
            'specialite': forms.TextInput(attrs={'class': 'form-control'}),
        }
class EvaluationForm(forms.ModelForm):
    class Meta:
        model = Stagiaire
        fields = ['rating', 'commentaire_evaluation']
        widgets = {
            'rating': forms.NumberInput(attrs={
                'min': 0,
                'max': 5,
                'class': 'form-control'
            }),
            'commentaire_evaluation': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Commentaire sur le stage...'
            })
        }
    