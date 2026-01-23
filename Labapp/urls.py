from django.urls import path
from . import views
from django.shortcuts import render   # <-- Ajouter ceci !

from .views import (
    RechercheCreateView, RechercheListView, RechercheUpdateView, RechercheDeleteView,
    AnalyseCreateView, AnalyseListView, AnalyseUpdateView, AnalyseDeleteView,
    BackRechercheListView,BackRechercheUpdateView,BackAnalyseListView ,BackRechercheDeleteView,BackAnalyseUpdateView,BackAnalyseDeleteView,
)

app_name = 'Labapp'

urlpatterns = [
    # ----------------------------
    # FRONT
    # ----------------------------
    path('', views.home, name='home'),
    path('index.html', views.home, name='home_html'),

    # Recherche front
    path('recherche/create/', RechercheCreateView.as_view(), name='recherche_create'),
    path('recherche/', RechercheListView.as_view(), name='recherche_list'),
    path('recherche/<int:pk>/update/', RechercheUpdateView.as_view(), name='recherche_update'),
    path('recherche/<int:pk>/delete/', RechercheDeleteView.as_view(), name='recherche_delete'),

    # Analyse front
    path('analyse/create/', AnalyseCreateView.as_view(), name='analyse_create'),
    path('analyse/', AnalyseListView.as_view(), name='analyse_list'),
    path('analyse/<int:pk>/update/', AnalyseUpdateView.as_view(), name='analyse_update'),
    path('analyse/<int:pk>/delete/', AnalyseDeleteView.as_view(), name='analyse_delete'),

    # ----------------------------
    # BACK
    # ----------------------------
    path('back/', views.back, name='back'),

    # Recherche back
    path('back/recherches/', BackRechercheListView.as_view(), name='back_recherche_list'),
    path('back/recherches/<int:pk>/update/', BackRechercheUpdateView.as_view(), name='back_recherche_update'),
    path('back/recherches/<int:pk>/delete/', BackRechercheDeleteView.as_view(), name='back_recherche_delete'),

      # Back Analyse list
    path('back/analyse/list/', BackAnalyseListView.as_view(), name='back_analyse_list'),
    path('back/analyse/<int:pk>/update/', BackAnalyseUpdateView.as_view(), name='back_analyse_update'),
    path('back/analyse/<int:pk>/delete/', BackAnalyseDeleteView.as_view(), name='back_analyse_delete'),
    path('analyse/<int:pk>/pdf/', views.analyse_pdf, name='analyse_pdf'),
    path('recherche/statistiques/', views.recherche_stats, name='recherche_stats'),
    path('notifications/analyses/', views.notifications_analyses_terminees, name='notifications_analyses_terminees'),
    path('map/', views.map_view, name='map'),
    path('chat/get_or_create/<str:doctor_id>/', views.get_or_create_room, name='get_or_create_room'),
    path('chat/<int:room_id>/data/', views.room_messages, name='room_messages'),
    path('chat/start/<str:doctor_id>/', views.start_private_chat, name='start_private_chat'),
    path('my-chat/', views.my_chat_redirect, name='my_chat_redirect'),
    path('chat/<int:room_id>/', views.chat_room, name='chat_room'),
    path('chat/<int:room_id>/send/', views.send_message, name='send_message'),
]