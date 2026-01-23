"""
URL configuration for Clinica project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.shortcuts import render
from django.contrib.auth import views as auth_views
from UserApp.views import *
from achatapp import views as achat_views
from django.conf import settings
from django.conf.urls.static import static
from gestionPatient.views import DashboardHomeView, LandingPageView, PublicAppointmentCreateView

def front_index(request):
    return render(request, 'Front/index.html')


def back_index(request):
    return render(request, 'Back/index2.html')


urlpatterns = [
    path('admin/', admin.site.urls),
    
    # Pages d'accueil
    path('', achat_views.index, name='index'),
    path('Front/home', front_index, name='front_index'), 
    path('Back/home', back_index, name='back_index'),
    path('home/', home, name='home'),
    
    # Routes Dashboard
    path('dashboard/', dashboard, name='dashboard'),
    path('dashboard/products/', achat_views.dashboard, name='dashboard_products'),
    path('dashboard/orders/', achat_views.orders_list, name='orders_list'),
    path('dashboard/orders/confirm/<int:order_id>/', achat_views.confirm_order, name='confirm_order'),
    path('dashboard/orders/reject/<int:order_id>/', achat_views.reject_order, name='reject_order'),
    path('products/', achat_views.products_list, name='products_list'),
    path('dashboard/orders/export-pdf/', achat_views.export_orders_pdf, name='export_orders_pdf'),
    path('dashboard/products/add/', achat_views.product_add, name='product_add'),
    path('dashboard/products/edit/<int:product_id>/', achat_views.product_edit, name='product_edit'),
    path('dashboard/products/delete/<int:product_id>/', achat_views.product_delete, name='product_delete'),
    
    # Routes User Management
    path('user/add/', add_user, name='add_user'),
    path('user/edit/<str:user_id>/', edit_user, name='edit_user'),
    path('user/delete/<str:user_id>/', delete_user, name='delete_user'),
    
    # Authentication routes
    path('loginBack/', auth_views.LoginView.as_view(template_name='Back/User/login.html'), name='loginBack'),
    path('logoutBack/', logout_back, name='logoutBack'),
    path('loginFront/', auth_views.LoginView.as_view(template_name='Front/User/login.html'), name='loginFront'),
    path('logoutFront/', logout_front, name='logoutFront'),
    path('forgot_password/',forgot_password, name='forgot_password'),
    path('verify_code/', verify_code, name='verify_code'),
    path('reset_password/', reset_password, name='reset_password'),
    path('loginBackCheck/', login_backoffice, name='loginBackCheck'),
    path('loginFrontCheck/',login_frontoffice,name='loginFrontCheck'),
    path('registerFront/',register_frontoffice,name='register_frontoffice'),
    path('registerBack/', register_backoffice, name='register_backoffice'),
    
    # Routes Product (achatapp)
    path('panier/', achat_views.panier, name='panier'),
    path('panier/ajouter/<int:produit_id>/', achat_views.ajouter_au_panier, name='ajouter_au_panier'),
    path('panier/modifier/<int:produit_id>/', achat_views.modifier_quantite_panier, name='modifier_quantite_panier'),
    path('panier/retirer/<int:produit_id>/', achat_views.retirer_du_panier, name='retirer_du_panier'),
    path('panier/vider/', achat_views.vider_panier, name='vider_panier'),
    path('panier/commander/', achat_views.passer_commande, name='passer_commande'),
    path('health-quiz/', achat_views.health_quiz, name='health_quiz'),
    path('payment/success/', achat_views.payment_success, name='payment_success'),
    path('payment/cancel/', achat_views.payment_cancel, name='payment_cancel'),
    path('order/track/<int:order_id>/<str:token>/', achat_views.order_tracking, name='order_tracking'),
    path('acheter/<int:produit_id>/', achat_views.acheter_produit, name='acheter_produit'),
    path('product/<int:product_id>/', achat_views.product_detail, name='product_detail'),
    path('api/product-suggestions/', achat_views.product_search_suggestions, name='product_search_suggestions'),
    
    # Pages diverses
    path('service-details/', achat_views.service_details, name='service_details'),
    path('starter-page/', achat_views.starter_page, name='starter_page'),
    
    # Module routes from GestionDonation
    path('publication/', include('Publication.urls', namespace='publication')),
    path('donation/', include('Donation.urls', namespace='donation')),

    #Module Labo
   # path('', include('Labapp.urls', namespace='Labapp')),  # homepage → Labapp
   # path('recherche/', include('Labapp.urls')),
    path('labo/', include('Labapp.urls', namespace='Labapp')),
    
     # GestionPatient explicit routes
    path('patient/dashboard/', DashboardHomeView.as_view(), name='dashboard_home'),

    path('appointment/', PublicAppointmentCreateView.as_view(), name='public_appointment'),
    path('patients/', include('gestionPatient.urls')),

    # Landing page from gestionPatient
    path('', LandingPageView.as_view(), name='site_home'),

    
    #Stage
    path('stages/', include('stages.urls')),  # → TOUT PASSE PAR stages/
    path('stagiaires/', include('stagiaire.urls')),
]


# Configuration pour servir les fichiers média et statiques en développement
if settings.DEBUG:
    from django.conf.urls.static import static
    from django.contrib.staticfiles.urls import staticfiles_urlpatterns
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += staticfiles_urlpatterns()
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATICFILES_DIRS[0])
    