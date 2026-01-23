from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.conf import settings
from Publication.models import Publication
import random
import string


def generate_short_token():
    return ''.join(random.choices(string.digits, k=6))


class Donation(models.Model):
    TYPE_CHOICES = [
        ('argent', 'Argent'),
        ('volontariat', 'Volontariat')
    ]
    
    METHODE_PAIEMENT_CHOICES = [
        ('stripe', 'Carte bancaire (Stripe)'),
        ('paypal', 'PayPal'),
        ('cheque', 'Chèque'),
    ]
    
    STATUT_CHOICES = [
        ('en_attente', 'En attente'),
        ('valide', 'Validé'),
        ('echec', 'Échec')
    ]
    
    id_donation = models.AutoField(primary_key=True)
    id_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='donations'
    )
    id_publication = models.ForeignKey(
        Publication,
        on_delete=models.CASCADE,
        related_name='donations'
    )
    type_donation = models.CharField(max_length=20, choices=TYPE_CHOICES)
    description = models.TextField(
        blank=True,
        null=True,
        help_text="Description du volontariat"
    )
    date_donation = models.DateTimeField(auto_now_add=True)
    montant = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True
    )
    methode_paiement = models.CharField(
        max_length=20,
        choices=METHODE_PAIEMENT_CHOICES,
        blank=True,
        null=True
    )
    statut = models.CharField(
        max_length=20,
        choices=STATUT_CHOICES,
        default='en_attente'
    )
    stripe_payment_intent = models.CharField(max_length=128, blank=True, null=True)
    telegram_chat_id = models.CharField(max_length=50, null=True, blank=True)

    class Meta:
        verbose_name = "Donation 💰"
        verbose_name_plural = "💰 Donation Management Dashboard 💰"
        ordering = ['-date_donation']
    
    def clean(self):
        if self.type_donation == 'argent':
            if not self.montant or self.montant <= 0:
                raise ValidationError("Le montant est obligatoire pour une donation d'argent")
            if not self.methode_paiement:
                raise ValidationError("La méthode de paiement est obligatoire pour une donation d'argent")
        
        if self.type_donation == 'volontariat':
            if not self.description:
                raise ValidationError("La description est obligatoire pour le volontariat")
            self.statut = 'valide'
    
    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"Donation {self.type_donation} - {self.id_user.username} - {self.id_publication.title}"


class TelegramLink(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="telegram_link"
    )
    chat_id = models.CharField(max_length=50, unique=True)
    linked_at = models.DateTimeField(auto_now_add=True)
    short_token = models.CharField(max_length=20, unique=True, null=True, blank=True)

    def __str__(self):
        return f"{self.user} -> {self.chat_id}"
    
    
    

class DonorBadge(models.Model):
    BADGE_CHOICES = [
        ("bronze", "Bronze Donor"),
        ("silver", "Silver Donor"),
        ("gold", "Gold Donor"),
        ("hero", "Hero Donor"),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="donor_badge")
    badge = models.CharField(max_length=20, choices=BADGE_CHOICES)
    earned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "badge")

    def __str__(self):
        return f"{self.user} → {self.get_badge_display()}"
