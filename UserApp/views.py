from django.urls import reverse_lazy
from django.views.generic import CreateView
from .forms import UserForm,UserEditForm
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from .models import User,PasswordResetCode
from django.contrib.auth import logout,login,authenticate,get_user_model
from django.contrib import messages
from django.contrib.auth.hashers import make_password
from django.db.models import Count
import json
import random
from django.core.mail import send_mail
from django.utils import timezone
from datetime import timedelta
from django.http import HttpResponse
from .decorators import role_required
def logout_front(request):
    logout(request)
    return redirect('loginFront')

def logout_back(request):
    logout(request)
    return redirect('loginBack')

@login_required(login_url='loginFront')
def home(request):
    return render(request, 'Front/User/home.html')

from django.contrib.auth import authenticate, login
from django.shortcuts import redirect
from django.contrib import messages

def login_frontoffice(request):
    if request.method == "POST":
        email = request.POST.get("email")
        password = request.POST.get("password")

        user = authenticate(request, username=email, password=password)

        if user is None:
            messages.error(request, "Invalid credentials")
            return redirect("loginFront")

        login(request, user)

        role_redirects = {
            'admin': 'admin_dashboard',
            'Dr': 'medical_dashboard',
            'nurse': 'medical_dashboard',
            'patient': 'patient_profile',
            'user': 'home',
            'intern': 'home',
        }

        return redirect(role_redirects.get(user.role, 'home'))

    return render(request, "Front/User/login.html")


def login_backoffice(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')

        # Authenticate using email instead of username
        user = authenticate(request, username=email, password=password)

        if user is not None:
            # Check if user role is admin for back office
            if user.role == 'admin':
                login(request, user)
                return redirect('dashboard')
            else:
                messages.error(request, "You are not allowed to access the back office.")
        else:
            messages.error(request, "Invalid email or password.")
    
    return render(request, 'Back/User/login.html')

User = get_user_model()


def register_frontoffice(request):
    if request.method == "POST":
        first_name = request.POST.get("first_name")
        last_name = request.POST.get("last_name")
        birth_date = request.POST.get("birth_date")
        tel = request.POST.get("tel")
        email = request.POST.get("email")
        CIN = request.POST.get("CIN")
        address = request.POST.get("address")
        password = request.POST.get("password")
        role=request.POST.get("role")
        user=User(
            first_name=first_name,
            last_name=last_name,
            birth_date=birth_date,
            tel=tel,
            email=email,
            CIN=CIN,
            address=address,
            role=role,
        )
        user.password = make_password(password)
        user.save()

        return redirect('home')

    return render(request, "Front/User/login.html")

def register_backoffice(request):
    if request.method == "POST":
        first_name = request.POST.get("first_name")
        last_name = request.POST.get("last_name")
        birth_date = request.POST.get("birth_date")
        tel = request.POST.get("tel")
        email = request.POST.get("email")
        CIN = request.POST.get("CIN")
        address = request.POST.get("address")
        password = request.POST.get("password")

        user = User(
            first_name=first_name,
            last_name=last_name,
            birth_date=birth_date,
            tel=tel,
            email=email,
            CIN=CIN,
            address=address,
            role='admin',
        )

        user.password = make_password(password)

        user.save()
        login(request, user)

        return redirect('dashboard')

    return render(request, "Back/User/login.html")

class RegisterView(CreateView):
    template_name='Front/User/register.html'
    form_class=UserForm
    success_url=reverse_lazy('loginFront')

#@role_required(['admin'])
#@login_required(login_url='loginBack')
def dashboard(request):
    users = User.objects.all()
    role_counts = User.objects.values('role').annotate(count=Count('role'))

    labels = [item['role'] for item in role_counts]
    quantities = [item['count'] for item in role_counts]
    context = {
        'users': users,
        'total_users': users.count(),
        'user_labels_json': json.dumps(labels),
        'user_quantities_json': json.dumps(quantities)
    }

    return render(request, 'Back/User/dashboard.html', context)

def edit_user(request, user_id):
    user = get_object_or_404(User, user_id=user_id)
    if request.method == 'POST':
        form = UserEditForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            return redirect('dashboard')
    else:
        form = UserEditForm(instance=user)
    return render(request, 'Back/User/user_form.html', {'form': form, 'title': 'Edit User'})

def delete_user(request, user_id):
    user = get_object_or_404(User, user_id=user_id)
    user.delete()
    return redirect("dashboard")


def add_user(request):
    if request.method == "POST":
        form = UserForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("dashboard")
    else:
        form = UserForm()
    return render(request, "Back/User/user_form.html", {"form": form, "title": "Add User"})

def forgot_password(request):
    if request.method == "POST":
        email = request.POST.get("email")

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            messages.error(request, "Email not found")
            return redirect('forgot_password')

        # Generate code
        code = str(random.randint(100000, 999999))
        PasswordResetCode.objects.create(user=user, code=code)

        # Send email
        send_mail(
            'Password Reset Code',
            f'Your reset code is: {code}',
            'yourgmail@gmail.com',
            [email],
            fail_silently=False,
        )

        # IMPORTANT FIX HERE
        return redirect(f'/verify_code/?email={email}')

    return render(request, "Front/User/forgot_password.html")


def verify_code(request):

    if request.method == "GET":
        email = request.GET.get("email", "")
        return render(request, "Front/User/verify_code.html", {"email": email})

    if request.method == "POST":
        email = request.POST.get("email")
        code = request.POST.get("code")

        try:
            user = User.objects.get(email=email)
            reset_entry = PasswordResetCode.objects.get(user=user, code=code)
        except:
            messages.error(request, "Invalid code or email")
            return redirect(f"/verify_code/?email={email}")

        # Check expiration
        if timezone.now() - reset_entry.created_at > timedelta(minutes=15):
            reset_entry.delete()
            messages.error(request, "Code expired")
            return redirect("forgot_password")

        # SAVE IN SESSION
        request.session['reset_user_id'] = user.user_id  
        request.session['reset_code'] = code  

        return redirect("reset_password")

def reset_password(request):
    user_id = request.session.get("reset_user_id")
    reset_code = request.session.get("reset_code")

    if not user_id or not reset_code:
        messages.error(request, "Invalid link or session expired.")
        return redirect("forgot_password")

    try:
        user = User.objects.get(user_id=user_id)
    except User.DoesNotExist:
        messages.error(request, "User not found.")
        return redirect("forgot_password")

    # Check that reset code exists
    if not PasswordResetCode.objects.filter(user=user, code=reset_code).exists():
        messages.error(request, "Reset code invalid or already used.")
        return redirect("forgot_password")

    if request.method == "POST":
        password1 = request.POST.get("password1")
        password2 = request.POST.get("password2")

        if not password1 or not password2:
            messages.error(request, "Please fill both password fields.")
            return render(request, "Front/User/reset_password.html", {
                "user_id": user_id,
                "code": reset_code
            })

        if password1 != password2:
            messages.error(request, "Passwords do not match.")
            return render(request, "Front/User/reset_password.html", {
                "user_id": user_id,
                "code": reset_code
            })

        user.set_password(password1)
        user.save()

        if user.check_password(password1):
            request.session.pop("reset_user_id", None)
            request.session.pop("reset_code", None)
            PasswordResetCode.objects.filter(user=user, code=reset_code).delete()

            messages.success(request, "Password updated successfully. You can now log in.")
            return redirect("loginFront")
        else:
            messages.error(request, "Password update failed.")
            return render(request, "Front/User/reset_password.html", {
                "user_id": user_id,
                "code": reset_code
            })

    # GET request: send user_id and code to template
    return render(request, "Front/User/reset_password.html", {
        "user_id": user_id,
        "code": reset_code
    })


# Create your views here.
