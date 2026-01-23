from django.contrib import admin
from django.contrib.admin import AdminSite
from .models import User


class MyAdminSite(AdminSite):
    site_header = "Clinica Dashboard"
    index_title = "Welcome to Clinica Admin"
    site_title = "Clinica Admin Panel"
    index_template = "dashboard.html"

my_admin_site = MyAdminSite(name='myadmin')



class UserAdmin(admin.ModelAdmin):
    list_display = ('user_id','first_name', 'last_name', 'CIN','birth_date', 'email', 'tel', 'address', 'role')
    search_fields = ('user_id', 'last_name', 'CIN', 'email')
    list_filter = ('first_name', 'last_name', 'role')

my_admin_site.register(User, UserAdmin)

# Register your models here.
