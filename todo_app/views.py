from django.shortcuts import render

# Create your views here.
# todo_app/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from stagiaire.models import Stagiaire
from .models import TodoItem  # ← IMPORT CORRECT
from .forms import TodoItemForm  # ← IMPORT DU FORMULAIRE

@login_required
def todo_list(request):
    # Vérifier si stagiaire validé
    try:
        stagiaire = Stagiaire.objects.get(user=request.user)
        if not stagiaire.est_valide:
            messages.warning(request, "Votre compte n'est pas encore validé.")
            return redirect('stages:liste_stages')
    except Stagiaire.DoesNotExist:
        messages.warning(request, "Vous n'êtes pas inscrit comme stagiaire.")
        return redirect('stages:liste_stages')
    
    # Récupérer les tâches
    todos = TodoItem.objects.filter(stagiaire=request.user)
    
    context = {
        'todo_items': todos.filter(status='todo'),
        'in_progress_items': todos.filter(status='in_progress'),
        'done_items': todos.filter(status='done'),
        'total_tasks': todos.count(),
    }
    
    return render(request, 'Front/to_do/todo_list.html', context)

@login_required
def todo_create(request):
    # Vérification stagiaire
    try:
        stagiaire = Stagiaire.objects.get(user=request.user)
        if not stagiaire.est_valide:
            return redirect('stages:liste_stages')
    except Stagiaire.DoesNotExist:
        return redirect('stages:liste_stages')
    
    if request.method == 'POST':
        form = TodoItemForm(request.POST)
        if form.is_valid():
            todo = form.save(commit=False)
            todo.stagiaire = request.user
            todo.save()
            messages.success(request, "Tâche ajoutée avec succès!")
            return redirect('todo:todo_list')
    else:
        form = TodoItemForm()
    
    return render(request, 'Front/to_do/todo_create.html', {'form': form})

@login_required
def todo_update_status(request, pk, new_status):
    try:
        todo = TodoItem.objects.get(id=pk, stagiaire=request.user)
        todo.status = new_status
        todo.save()
        messages.success(request, "Statut mis à jour!")
    except TodoItem.DoesNotExist:
        messages.error(request, "Tâche non trouvée")
    
    return redirect('todo:todo_list')


@login_required
def todo_delete(request, pk):
    try:
        todo = TodoItem.objects.get(id=pk, stagiaire=request.user)
        todo.delete()
        messages.success(request, "Tâche supprimée!")
    except TodoItem.DoesNotExist:
        messages.error(request, "Tâche non trouvée")
    
    return redirect('todo:todo_list')