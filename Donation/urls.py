from django.urls import path
from .views import *
from . import views

app_name = 'donation'

urlpatterns = [

    path('dashboard/', back_index, name='back_index'), 
    # BACKEND (ADMIN)
    path('admin/list/', AdminDonationListView.as_view(), name='admin_donation_list'),
    path('admin/detail/<int:pk>/', AdminDonationDetailView.as_view(), name='admin_donation_detail'),
    path('admin/delete/<int:pk>/', AdminDonationDeleteView.as_view(), name='admin_donation_delete'),
    
    # FRONTEND (USER)
    path('publications/', FrontPublicationListView.as_view(), name='front_publication_list'),
    path('publications/<int:pk>/', FrontPublicationDetailView.as_view(), name='front_publication_detail'),
    path('create/', FrontDonationCreateView.as_view(), name='donation_create'),
    path('my-donations/', UserDonationListView.as_view(), name='user_donation_list'),
    path('delete/<int:pk>/', UserDonationDeleteView.as_view(), name='user_donation_delete'),
    #stripe
    path("pay/<int:pub_id>/", views.donation_payment, name="donation_payment"),
 
    path("ajax/create-payment-intent/", views.create_payment_intent, name="create_payment_intent"),

    path('create/<int:donation_id>/checkout/', 
         views.create_checkout_session, 
         name='create_checkout_session'),
    path('stripe/success/<int:donation_id>/', 
         views.stripe_success, 
         name='stripe_success'),
    path('stripe/cancel/<int:donation_id>/', 
         views.stripe_cancel, 
         name='stripe_cancel'),
    path("telegram/connect/", views.telegram_connect, name="telegram_connect"),
    path("telegram/webhook/<str:secret>/", views.telegram_webhook, name="telegram_webhook"),


    path('stripe/success/<int:donation_id>/', views.stripe_success, name='stripe_success'),
    path('export/pdf/', views.export_donations_pdf, name='export_donations_pdf'),

    path('receipt/<int:donation_id>/', views.donation_receipt, name='donation_receipt'),
    path('receipt/pdf/<int:donation_id>/', views.donation_receipt_pdf, name='donation_receipt_pdf'),


]
