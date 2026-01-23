from django.urls import path
from . import views

app_name = 'stagiaire'

urlpatterns = [
    path('deposer/<int:stage_id>/', views.deposer_candidature, name='ajout_public'),
    path('liste/', views.liste_stagiaires, name='liste_stagiaires'),
    path('valider/<str:user_id>/', views.valider_stagiaire, name='valider_stagiaire'),
    # AJOUTEZ CES DEUX URLs
    path('evaluer/<str:user_id>/', views.evaluer_stagiaire, name='evaluer_stagiaire'),
    path('evaluer-ajax/<str:user_id>/', views.evaluer_stagiaire_ajax, name='evaluer_stagiaire_ajax'),
    path('calendrier/', views.calendrier_stages, name='calendrier_stages'),
]