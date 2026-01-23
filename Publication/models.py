from django.db import models
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator, FileExtensionValidator, MinLengthValidator
from django.utils import timezone
# Create your models here.

ValidTitle=RegexValidator(r'^[A-Za-z\s]+$','Only alphabetic caracters or espaces are allowed.')

class Publication(models.Model):
    title=models.CharField(max_length=100,validators=[ValidTitle])
    description=models.TextField(validators=[MinLengthValidator(30,"Description must be at least 30 characters long.")])
    date_pub=models.DateTimeField(auto_now_add=True)
    deadline=models.DateField(help_text="Date limite ou échéance")
    address=models.CharField(max_length=30, help_text="Lieu concerné par la publication")
    pubPicture=models.FileField(upload_to="PubPictures/",validators=[FileExtensionValidator(allowed_extensions=['png','jpg','jpeg'])], help_text="Chemin vers l'image associée")

    class Meta:
        verbose_name = "Publication 📅"
        verbose_name_plural = "📅 Publication Management Dashboard 📅"
        

    def clean(self):
        today=timezone.now().date()
        if not self.deadline>=today:
            raise ValidationError("Deadline must be in the future.")