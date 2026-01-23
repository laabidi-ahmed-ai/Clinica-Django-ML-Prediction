from django import forms
from .models import Recherche, Analyse

# ----------------------------
# Formulaire Recherche
# ----------------------------
class RechercheForm(forms.ModelForm):
    class Meta:
        model = Recherche
        fields = [
            'nom_recherche', 'maladie', 'objectif', 'date_deb', 'date_fin',
            'risque', 'type_recherche', 'budget', 'etat', 'publication_associee',
            'resultats_obtenus', 'equipement', 'responsable'
        ]
        widgets = {
            'nom_recherche': forms.TextInput(attrs={'class': 'form-control', 'required': True}),
            'maladie': forms.TextInput(attrs={'class': 'form-control', 'required': True}),
            'objectif': forms.Textarea(attrs={'class': 'form-control', 'required': True}),
            'date_deb': forms.DateInput(attrs={'type': 'date', 'class': 'form-control', 'required': True}),
            'date_fin': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'type_recherche': forms.Select(attrs={'class': 'form-select', 'required': True}),
            'budget': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'etat': forms.Select(attrs={'class': 'form-select', 'required': True}),
            'publication_associee': forms.URLInput(attrs={'class': 'form-control'}),
            'resultats_obtenus': forms.Textarea(attrs={'class': 'form-control'}),
            'equipement': forms.Select(attrs={'class': 'form-select'}),
            'responsable': forms.Select(attrs={'class': 'form-select'}),
        }

    def clean_nom_recherche(self):
        nom = self.cleaned_data.get('nom_recherche')
        if not nom:
            raise forms.ValidationError("Nom requis")
        if not nom.replace(" ", "").isalpha():
            raise forms.ValidationError("Nom: lettres seulement")
        return nom

    def clean_maladie(self):
        maladie = self.cleaned_data.get('maladie')
        if not maladie:
            raise forms.ValidationError("Maladie requise")
        if not maladie.replace(" ", "").isalpha():
            raise forms.ValidationError("Maladie: lettres seulement")
        return maladie

    def clean_objectif(self):
        objectif = self.cleaned_data.get('objectif')
        if not objectif:
            raise forms.ValidationError("Objectif requis")
        if len(objectif) < 50:
            raise forms.ValidationError("Objectif: minimum 50 caractères")
        return objectif

    def clean(self):
        cleaned_data = super().clean()
        date_deb = cleaned_data.get('date_deb')
        date_fin = cleaned_data.get('date_fin')
        if date_deb and date_fin and date_deb > date_fin:
            self.add_error('date_deb', "Date début doit être avant date fin")

# ----------------------------
# Formulaire Analyse
# ----------------------------
class AnalyseForm(forms.ModelForm):
    class Meta:
        model = Analyse
        fields = [
            'type', 'category', 'echantillon_code', 'patient_id',
            'technique_utilisee', 'date_prelevement', 'date_res', 'etat',
            'cout', 'commentaire', 'equipement', 'responsable',
            'responsable_analyse', 'valide_par'
        ]
        widgets = {
            'type': forms.Select(attrs={'class': 'form-select', 'required': True}),
            'category': forms.TextInput(attrs={'class': 'form-control'}),
            'echantillon_code': forms.TextInput(attrs={'class': 'form-control', 'required': True}),
            'patient_id': forms.TextInput(attrs={'class': 'form-control'}),
            'technique_utilisee': forms.TextInput(attrs={'class': 'form-control'}),
            'date_prelevement': forms.DateInput(attrs={'type': 'date','class': 'form-control', 'required': True}),
            'date_res': forms.DateInput(attrs={'type': 'date','class': 'form-control'}),
            'etat': forms.Select(attrs={'class': 'form-select','required': True}),
            'cout': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'commentaire': forms.Textarea(attrs={'class': 'form-control','rows':3}),
            'equipement': forms.Select(attrs={'class': 'form-select'}),
            'responsable': forms.Select(attrs={'class': 'form-select'}),
            'responsable_analyse': forms.Select(attrs={'class': 'form-select'}),
            'valide_par': forms.Select(attrs={'class': 'form-select'}),
        }
