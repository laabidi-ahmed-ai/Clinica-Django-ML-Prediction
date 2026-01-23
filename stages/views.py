from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import Stage

from stagiaire.models import Stagiaire
from stagiaire.forms import PublicStagiaireForm
from stages.forms import StageForm
from UserApp.models import User

def ajouter_stage(request):
    if request.method == 'POST':
        form = StageForm(request.POST)
        if form.is_valid():
            stage = form.save(commit=False)
            # Gérer les valeurs vides pour stagiaire et encadrant
            
            if not request.POST.get('encadrant'):
                stage.encadrant = None
            stage.save()
            messages.success(request, 'Stage ajouté avec succès!')
            return redirect('stages:liste_stages')
    else:
        form = StageForm()
    
    # Passer les listes de stagiaires et encadrants au template
    #stagiaires = Stagiaire.objects.all()
    encadrants = User.objects.filter(role='Dr')
    
    return render(request, 'Back/stage/create_stage.html', {
        'form': form,
        
        'encadrants': encadrants
    })


def modifier_stage(request, pk):
    stage = get_object_or_404(Stage, pk=pk)
    if request.method == 'POST':
        form = StageForm(request.POST, instance=stage)
        if form.is_valid():
            stage = form.save(commit=False)
            # Gérer les valeurs vides pour stagiaire et encadrant
            
            if not request.POST.get('encadrant'):
                stage.encadrant = None
            stage.save()
            messages.success(request, 'Stage modifié avec succès!')
            return redirect('stages:liste_stages')
    else:
        form = StageForm(instance=stage)
    
    # Passer les listes de stagiaires et encadrants au template
    
    encadrants = User.objects.filter(role='Dr')
    
    return render(request, 'back/stage/update_stage.html', {
        'form': form,
        'stage': stage,
        'encadrants': encadrants
    })

def supprimer_stage(request, pk):
    stage = get_object_or_404(Stage, pk=pk)
    if request.method == 'POST':
        stage.delete()
        messages.success(request, 'Stage supprimé avec succès!')
        return redirect('stages:liste_stages')
    
    return render(request, 'Back/stage/delete_stage.html', {'stage': stage})

def liste_stages_front(request):
    """Vue front-end pour lister les stages disponibles - Accès public sans authentification"""
    stages = Stage.objects.all().order_by('-date_debut')
    
    # Créer un formulaire vide pour les modals
    form = PublicStagiaireForm()
    
    context = {
        'stages': stages,
        'form': form,  # Ajouter le formulaire au contexte
    }
    return render(request, 'Front/stages/liste_stages.html', context)

def liste_stages(request):
    stages = Stage.objects.all().select_related('encadrant')

    # Récupérer les filtres depuis la requête GET
    search_query = request.GET.get('search', '')
    encadrant_query = request.GET.get('encadrant', '')
    type_stage_filter = request.GET.get('type_stage', '')
    statut_filter = request.GET.get('statut', '')
    date_debut_filter = request.GET.get('date_debut', '')
    date_fin_filter = request.GET.get('date_fin', '')

    # Filtres
    if search_query:
        stages = stages.filter(intitule__icontains=search_query)

    if encadrant_query:
        stages = stages.filter(
            encadrant__first_name__icontains=encadrant_query
        ) | stages.filter(
            encadrant__last_name__icontains=encadrant_query
        )

    if type_stage_filter:
        stages = stages.filter(type_stage=type_stage_filter)

    if statut_filter:
        stages = stages.filter(statut=statut_filter)

    if date_debut_filter:
        stages = stages.filter(date_debut__gte=date_debut_filter)

    if date_fin_filter:
        stages = stages.filter(date_fin__lte=date_fin_filter)

    context = {
        'stages': stages,
        'search_query': search_query,
        'encadrant_query': encadrant_query,
        'type_stage_filter': type_stage_filter,
        'statut_filter': statut_filter,
        'date_debut_filter': date_debut_filter,
        'date_fin_filter': date_fin_filter,
    }

    return render(request, 'Back/stage/read_stage.html', context)