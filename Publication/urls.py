from django.urls import path
from .import views
app_name = 'publication' 
from .views import *


"""
Une liste qui contient toutes les routes définies pour l'application Publication.
Chaque route est associée à une vue (fonction ou classe) et possède un nom unique.
"""

urlpatterns = [
 
    path('list/', PublicationListView.as_view(), name='publication_list'),
    
    
    path('detail/<int:pk>/', PublicationDetailView.as_view(), name='publication_detail'),
    
  
    path('create/', PublicationCreateView.as_view(), name='publication_form'),
    
    
    path('update/<int:pk>/', PublicationUpdateView.as_view(), name='publication_update'),
    
   
    path('delete/<int:pk>/', PublicationDeleteView.as_view(), name='publication_delete'),

]
