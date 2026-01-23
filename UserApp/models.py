from django.contrib.auth.models import AbstractBaseUser,BaseUserManager,PermissionsMixin
from django.db import models
from django.core.validators import RegexValidator
from django.core.exceptions import ValidationError
import uuid
nameValidator=RegexValidator(r'^[A-Za-z\s]+$','Only alphabetic char are allowed.')
telValidator=RegexValidator(r'^\+?\d{8,15}$','Only Phone Number format is allowed.')
CINvalidator=RegexValidator(r'^\d{8}$','Only Phone Number format is allowed.')
def generate_user_id():
    # Génère un identifiant unique du type user-XXXXXX (6 caractères alphanumériques)
    return "user" + uuid.uuid4().hex[:4].upper()

class UserManager(BaseUserManager):
    def create_user(self, email, first_name, last_name, tel, CIN, password=None, **extra_fields):

        if not first_name or not last_name or not tel or not CIN or not email:
            raise ValueError("first_name, last_name, tel, email and CIN are required")
        email = self.normalize_email(email)
        if 'user_id' not in extra_fields or not extra_fields['user_id']:
            new_id = generate_user_id()
            while User.objects.filter(user_id=new_id).exists():
                new_id = generate_user_id()
                extra_fields['user_id'] = new_id
        user = self.model(

            email=email,
            first_name=first_name,
            last_name=last_name,
            tel=tel,
            CIN=CIN,
            **extra_fields
        )
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, first_name, last_name, tel, CIN, password=None, **extra_fields):
        extra_fields['role'] = 'admin'
        return self.create_user(email, first_name, last_name, tel, CIN, password, **extra_fields)



class User(AbstractBaseUser,PermissionsMixin):
    ROLE_CHOICES=[('admin','Administrator'),('Dr','Doctor'),
        ('intern','Intern'),('patient','Patient'),('user','User'),('nurse','Nurse')]
    user_id=models.CharField(max_length=8,primary_key=True,unique=True,editable=False,default=generate_user_id)
    first_name=models.CharField(max_length=150,blank=False,validators=[nameValidator])
    last_name=models.CharField(max_length=150,blank=False,validators=[nameValidator])
    birth_date=models.DateField(null=True,blank=True)
    email=models.EmailField(unique=True)
    tel=models.CharField(unique=True,blank=False,validators=[telValidator])
    address=models.CharField(max_length=50)
    CIN=models.CharField(unique=True,blank=False,validators=[CINvalidator])
    role=models.CharField(max_length=20,choices=ROLE_CHOICES,default='user')
    objects = UserManager()
    USERNAME_FIELD='email'
    REQUIRED_FIELDS = ['first_name', 'last_name', 'tel', 'CIN']
    def __str__(self):
        return f"{self.user_id} ({self.role})"

class PasswordResetCode(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.email} - {self.code}"
# Create your models here.
  #manque Medecinnnnn