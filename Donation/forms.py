from django import forms
from .models import Donation

class DonationForm(forms.ModelForm):

    telegram_chat_id = forms.CharField(
        required=False,
        label="Votre Telegram Chat ID",
        widget=forms.TextInput(attrs={
            "placeholder": "Ex : 123456789",
            "class": "form-control"
        })
    )

    class Meta:
        model = Donation
        fields = [
            'id_publication',
            'type_donation',
            'montant',
            'methode_paiement',
            'description',
            'telegram_chat_id'
        ]

        widgets = {
            'id_publication': forms.Select(attrs={
                'class': 'form-select form-control',
                'id': 'id_publication'
            }),
            'type_donation': forms.Select(attrs={
                'class': 'form-select form-control',
                'id': 'id_type_donation'
            }),
            'montant': forms.NumberInput(attrs={
                'class': 'form-control',
                'id': 'id_montant',
                'placeholder': 'Custom amount',
                'step': '0.01',
                'min': '1'
            }),
            'methode_paiement': forms.Select(attrs={
                'class': 'form-select form-control',
                'id': 'id_methode_paiement'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'id': 'id_description',
                'rows': 4,
                'placeholder': 'Describe your volunteering contribution...'
            }),
        }

        labels = {
            'id_publication': 'Publication',
            'type_donation': 'Type de donation',
            'montant': 'Montant',
            'methode_paiement': 'Méthode de paiement',
            'description': 'Description',
            'telegram_chat_id': 'Telegram Chat ID'
        }

    def __init__(self, *args, **kwargs):
        publication_id = kwargs.pop('publication_id', None)
        super().__init__(*args, **kwargs)

        # Forcer la publication si fournie
        if publication_id:
            self.fields['id_publication'].initial = publication_id
            self.fields['id_publication'].widget = forms.HiddenInput()

        self.fields['type_donation'].choices = [
            ('', '--- Choisissez ---'),
            ('argent', '💸 Argent'),
            ('volontariat', '💝 Volontariat'),
        ]

        self.fields['methode_paiement'].choices = [
            ('', '--- Choisissez ---'),
            ('stripe', '💳 Carte bancaire (Stripe)'),
            ('paypal', '🅿️ PayPal'),
            ('cheque', '🧾 Chèque'),
        ]

        # Champs optionnels
        self.fields['montant'].required = False
        self.fields['methode_paiement'].required = False
        self.fields['description'].required = False
        self.fields['telegram_chat_id'].required = False
