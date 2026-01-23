from django import forms
from .models import Publication


class PublicationForm(forms.ModelForm):
    """Formulaire pour créer/modifier une publication"""
    class Meta:
        model = Publication
        fields = ['title', 'description', 'deadline', 'address', 'pubPicture']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Titre de la publication'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 6, 'placeholder': 'Description détaillée (minimum 30 caractères)'}),
            'deadline': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'address': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Adresse'}),
            'pubPicture': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/png,image/jpeg,image/jpg'}),
        }
        labels = {
            'title': 'Titre',
            'description': 'Description',
            'deadline': 'Deadline',
            'address': 'Adresse',
            'pubPicture': 'Image',
        }
