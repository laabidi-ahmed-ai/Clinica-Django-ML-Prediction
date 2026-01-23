from django.urls import path
from . import views 
from .views import *

urlpatterns = [
    path('', views.PatientListView.as_view(), name='patient_list'),
    path('<int:pk>/', views.PatientDetailView.as_view(), name='patient_detail'),
    path('<int:pk>/medical-history/', views.PatientMedicalHistoryView.as_view(), name='patient_medical_history'),
    path('<int:pk>/export-pdf/', views.export_patient_pdf, name='patient_export_pdf'),
    path('add/', views.PatientCreateView.as_view(), name='patient_add'),
    path('<int:pk>/edit/', views.PatientUpdateView.as_view(), name='patient_edit'),
    path('<int:pk>/delete/', views.PatientDeleteView.as_view(), name='patient_delete'),
    path('appointments/new/', views.AppointmentCreateView.as_view(), name='appointment_create'),
    path('appointments/success/', views.AppointmentSuccessView.as_view(), name='appointment_success'),
    path('appointments/', views.AppointmentListView.as_view(), name='appointment_list'),
    path('appointments/<int:pk>/', views.AppointmentDetailView.as_view(), name='appointment_detail'),
    path('appointments/<int:pk>/manage/', views.AppointmentUpdateView.as_view(), name='appointment_manage'),
    path('appointments/<int:appointment_id>/pay/', views.mark_payment, name='mark_payment'),
    #add
    path('appointment/', PublicAppointmentCreateView.as_view(), name='public_appointment'),
    path('my-portal/', views.MyPatientPortalView.as_view(), name='my_patient_portal'),
    
    # Messaging URLs
    path('messages/', views.MessagesListView.as_view(), name='messages_list'),
    path('messages/<int:patient_id>/', views.MessageConversationView.as_view(), name='message_conversation'),

]
