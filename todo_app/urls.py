from django.urls import path
from . import views

app_name = 'todo'

urlpatterns = [
    path('', views.todo_list, name='todo_list'),
    path('nouveau/', views.todo_create, name='todo_create'),
    path('<int:pk>/<str:new_status>/', views.todo_update_status, name='todo_update_status'),
    path('<int:pk>/supprimer/', views.todo_delete, name='todo_delete'),
]