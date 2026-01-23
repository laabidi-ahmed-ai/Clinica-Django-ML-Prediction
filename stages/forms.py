from django import forms
from .models import Stage
from stagiaire.models import Stagiaire

from UserApp.models import User


class StageForm(forms.ModelForm):
    class Meta:
        model = Stage
        fields = [
            'intitule', 'description', 'objectifs', 'type_stage', 'service',
            'date_debut', 'date_fin', 'duree_semaines', 'horaires_travail',
            'statut', 'encadrant',
            'acces_logiciel_medical', 'badge_acces', 'vestiaire_attribue'
        ]
        widgets = {
            'date_debut': forms.DateInput(attrs={'type': 'date'}),
            'date_fin': forms.DateInput(attrs={'type': 'date'}),
            'description': forms.Textarea(attrs={'rows': 4}),
            'objectifs': forms.Textarea(attrs={'rows': 3}),
            'horaires_travail': forms.TextInput(attrs={'placeholder': 'Ex: 8h-16h'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Stagiaires
        

        # Encadrants = liste des docteurs (role == 'Dr')
        self.fields['encadrant'].queryset = User.objects.filter(role='Dr')
        self.fields['encadrant'].required = False
        self.fields['encadrant'].empty_label = "Aucun encadrant (optionnel)"