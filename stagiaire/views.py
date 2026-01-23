# stagiaire/views.py
# stagiaire/views.py - CORRIGEZ LES IMPORTS
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from django.http import JsonResponse, HttpResponse  # AJOUTEZ CET IMPORT
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt  # AJOUTEZ CET IMPORT
from stages.models import Stage
from .models import Stagiaire
from .forms import PublicStagiaireForm, EvaluationForm  # AJOUTEZ EvaluationForm
import json
from datetime import datetime, timedelta
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_POST

# stagiaire/views.py - CORRIGEZ CETTE VUE
def calendrier_stages(request):
    """
    Calendrier des stages avec données réelles
    """
    # Récupérer tous les stagiaires avec leurs stages
    stagiaires = Stagiaire.objects.filter(est_valide=True).select_related('user').prefetch_related('stages')
    
    events = []
    
    for stagiaire in stagiaires:
        for stage in stagiaire.stages.all():
            try:
                # Calculer la couleur en fonction du type de stage
                type_colors = {
                    'observation': '#FF6B6B',
                    'clinique': '#4ECDC4',
                    'chirurgical': '#45B7D1',
                    'urgence': '#FFA726',
                    'specialise': '#AB47BC',
                    'recherche': '#26C6DA',
                    'infirmier': '#66BB6A'
                }
                
                color = type_colors.get(stage.type_stage, '#667eea')
                
                # Déterminer le statut pour la couleur
                today = timezone.now().date()
                if stage.date_debut <= today <= stage.date_fin:
                    status = 'En Cours'
                elif today > stage.date_fin:
                    status = 'Terminé'
                    color = '#66BB6A'
                else:
                    status = 'À Venir'
                
                # Récupérer le nom de l'encadrant de manière sécurisée
                encadrant_nom = "Non assigné"
                if stage.encadrant:
                    encadrant_nom = f"{stage.encadrant.first_name} {stage.encadrant.last_name}"
                
                event = {
                    'id': f"{stage.id}_{stagiaire.id}",
                    'title': f"{stagiaire.user.first_name} - {stage.intitule[:30]}",
                    'start': stage.date_debut.isoformat(),
                    'end': (stage.date_fin + timedelta(days=1)).isoformat(),
                    'color': color,
                    'extendedProps': {
                        'stagiaire_nom': f"{stagiaire.user.first_name} {stagiaire.user.last_name}",
                        'stagiaire_email': stagiaire.user.email,
                        'stagiaire_universite': stagiaire.universite,
                        'stagiaire_specialite': stagiaire.specialite or "Non spécifiée",
                        'intitule': stage.intitule,
                        'type_stage': stage.get_type_stage_display(),
                        'service': stage.get_service_display(),
                        'duree_semaines': stage.duree_semaines,
                        'horaires': stage.horaires_travail or 'Non spécifié',
                        'encadrant': encadrant_nom,
                        'status': status,
                        'description': stage.description[:100] + "..." if len(stage.description) > 100 else stage.description,
                    }
                }
                events.append(event)
            except Exception as e:
                print(f"Erreur avec le stage {stage.id}: {e}")
                continue
    
    # Statistiques pour le template
    total_stages = Stage.objects.count()
    
    # Calculer les stages en cours
    today = timezone.now().date()
    stages_en_cours = Stage.objects.filter(
        date_debut__lte=today,
        date_fin__gte=today
    ).count()
    
    # Calculer les stages terminés
    stages_termines = Stage.objects.filter(date_fin__lt=today).count()
    
    # Stagiaires actifs (validés)
    stagiaires_actifs = Stagiaire.objects.filter(est_valide=True).count()
    
    context = {
        'events_json': json.dumps(events),
        'total_stages': total_stages,
        'stages_en_cours': stages_en_cours,
        'stages_termines': stages_termines,
        'stagiaires_actifs': stagiaires_actifs,
        'type_colors': {
            'observation': '#FF6B6B',
            'clinique': '#4ECDC4',
            'chirurgical': '#45B7D1',
            'urgence': '#FFA726',
            'specialise': '#AB47BC',
            'recherche': '#26C6DA',
            'infirmier': '#66BB6A'
        }
    }
    
    return render(request, 'back/stagiaire/calendrier_stages.html', context)
   
    
def valider_stagiaire(request, user_id):
    # Valider le stagiaire
    stagiaire = get_object_or_404(Stagiaire, user__user_id=user_id)
    stagiaire.est_valide = True
    
    stagiaire.save()
    
    messages.success(request, f"✅ Stagiaire {stagiaire.user.first_name} validé avec succès!")
    return redirect('stagiaire:liste_stagiaires')
def deposer_candidature(request, stage_id):
    if not request.user.is_authenticated:
        messages.error(request, "Vous devez être connecté pour postuler à un stage.")
        return redirect('loginFront')

    # On récupère le stage avec l'ID passé dans l'URL
    stage = get_object_or_404(Stage, id=stage_id)

    # Récupère ou crée le stagiaire correspondant à l'utilisateur connecté
    stagiaire, created = Stagiaire.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        form = PublicStagiaireForm(request.POST, instance=stagiaire)
        if form.is_valid():
            stagiaire = form.save(commit=False)
            stagiaire.user = request.user
            stagiaire.save()

            # Ajoute le stage au ManyToMany
            stagiaire.stages.add(stage)

            messages.success(request, f"Votre candidature pour '{stage.intitule}' a été déposée avec succès !")
            return redirect('stagiaire:liste_stagiaires')

    else:
        form = PublicStagiaireForm(instance=stagiaire)

    return render(request, 'Front/stages/liste_stages.html', {
        'form': form,
        'stage': stage,
        'stages': Stage.objects.all()
    })

# stagiaire/views.py - MODIFIEZ LA VUE liste_stagiaires
def liste_stagiaires(request):
    stagiaires = Stagiaire.objects.all().select_related('user')
    
    # Calculer les statistiques
    total_stagiaires = stagiaires.count()
    
    # Nombre d'universités différentes
    universites_distinctes = stagiaires.values('universite').distinct().count()
    
    # Nombre de stagiaires validés
    stagiaires_valides = stagiaires.filter(est_valide=True).count()
    
    # Calculer le nombre de candidatures (stages postulés)
    total_candidatures = 0
    for stagiaire in stagiaires:
        total_candidatures += stagiaire.stages.count()
    
    context = {
        'stagiaires': stagiaires,
        'total_stagiaires': total_stagiaires,
        'universites_distinctes': universites_distinctes,
        'stagiaires_valides': stagiaires_valides,
        'total_candidatures': total_candidatures,
    }
    
    return render(request, 'back/stagiaire/liste_stagiaires.html', context)

def evaluer_stagiaire(request, user_id):
    if not request.user.is_authenticated or request.user.role != 'admin':
        messages.error(request, "Accès non autorisé.")
        return redirect('stagiaire:liste_stagiaires')
    
    stagiaire = get_object_or_404(Stagiaire, user__user_id=user_id)
    
    if request.method == 'POST':
        form = EvaluationForm(request.POST, instance=stagiaire)
        if form.is_valid():
            stagiaire_eval = form.save(commit=False)
            stagiaire_eval.date_evaluation = timezone.now()
            stagiaire_eval.save()
            
            messages.success(request, f"Évaluation enregistrée pour {stagiaire.user.first_name} !")
            return redirect('stagiaire:liste_stagiaires')
    else:
        form = EvaluationForm(instance=stagiaire)
    
    return render(request, 'back/stagiaire/evaluer_stagiaire.html', {
        'stagiaire': stagiaire,
        'form': form
    })

# stagiaire/views.py - MODIFIEZ LA VUE evaluer_stagiaire_ajax


# stagiaire/views.py - REMPLACEZ LA VUE AJAX


@require_POST
@csrf_protect
def evaluer_stagiaire_ajax(request, user_id):
    """Vue AJAX pour évaluation rapide"""
    if request.user.is_authenticated:
        try:
            stagiaire = Stagiaire.objects.get(user__user_id=user_id)
            # Essayer de lire les données JSON
            if request.content_type == 'application/json':
                data = json.loads(request.body)
                rating = int(data.get('rating', 0))
            else:
                # Fallback pour FormData
                rating = int(request.POST.get('rating', 0))
            
            if 0 <= rating <= 5:
                stagiaire.rating = rating
                stagiaire.date_evaluation = timezone.now()
                stagiaire.save()
                
                # Retourner une réponse JSON complète
                return JsonResponse({
                    'success': True,
                    'rating': rating,
                    'stars': '★' * rating + '☆' * (5 - rating),
                    'message': 'Évaluation enregistrée avec succès!'
                })
            else:
                return JsonResponse({
                    'success': False,
                    'error': 'La note doit être entre 0 et 5'
                })
                
        except Stagiaire.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Stagiaire non trouvé'
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })
    
    return JsonResponse({'success': False, 'error': 'Non authentifié'})