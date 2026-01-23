from .models import User
from django import forms
from django.contrib.auth.forms import UserCreationForm

class UserForm(UserCreationForm):
    role = forms.ChoiceField(choices=User.ROLE_CHOICES, widget=forms.Select(attrs={'class': 'form-select'}))
    class Meta:
        model = User
        fields = ["first_name","last_name","CIN","birth_date","address","email",'password1','password2','role','tel']
        labels={
            
            'first_name': 'First Name',
            'last_name': 'Last Name',
            'role': 'Role',
            'email':'Email',
            'CIN':'National ID Number',
            'birth_date':'Birth Date',
            'address':'Address',
            'tel':'Cell Phone Number',
        }
        widgets={
            'email':forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Enter email'}),
            'birth_date':forms.DateInput(attrs={'type':'date','class':'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'First Name'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Last Name'}),
            'password1': forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Password'}),
            'password2': forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Confirm'}),
        }
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['role'].choices = [choice for choice in User.ROLE_CHOICES if choice[0] != 'admin']
class UserEditForm(forms.ModelForm):
    role = forms.ChoiceField(choices=User.ROLE_CHOICES, widget=forms.Select(attrs={'class': 'form-select'}))
    class Meta:
        model = User
        fields = ["first_name","last_name","CIN","birth_date","address","email",'role','tel']
        labels={
            
            'first_name': 'First Name',
            'last_name': 'Last Name',
            'role': 'Role',
            'email':'Email',
            'CIN':'National ID Number',
            'birth_date':'Birth Date',
            'address':'Address',
            'tel':'Cell Phone Number',
        }
        widgets={
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Enter email'}),
            'birth_date': forms.DateInput(attrs={'type':'date','class':'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'First Name'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Last Name'}),
            'tel': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Cell phone'}),
            'address': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Address'}),
            'CIN': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'National ID'}),
        }