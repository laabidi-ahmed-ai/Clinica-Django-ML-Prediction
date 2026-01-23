from django.urls import path
from . import views

app_name = 'stages'

urlpatterns = [
    path('', views.liste_stages, name='liste_stages'),                    # → /stages/
    path('ajouter/', views.ajouter_stage, name='ajouter_stage'),          # → /stages/ajouter/
    path('<int:pk>/modifier/', views.modifier_stage, name='modifier_stage'), # → /stages/1/modifier/
    path('<int:pk>/supprimer/', views.supprimer_stage, name='supprimer_stage'), # → /stages/1/supprimer/
    
    # Front-end
    path('public/', views.liste_stages_front, name='liste_stages_front'),  # → /stages/public/
]