from django.shortcuts import render
from django.urls import reverse_lazy
from django.views.generic import CreateView, UpdateView, ListView, DeleteView
from .models import Recherche, Analyse
from .forms import RechercheForm, AnalyseForm
from django.shortcuts import redirect
from django.contrib import messages
from django.db.models import Q

# Home
from django.http import HttpResponse
from django.template.loader import render_to_string
from xhtml2pdf import pisa
from .models import Analyse
from django.contrib.auth import get_user_model

from django.contrib.auth.models import User

import matplotlib.pyplot as plt
import io
import base64
from django.db.models import Count, Sum
import matplotlib
matplotlib.use('Agg')  # backend pour serveur, pas de GUI
from django.http import JsonResponse
# views.py
from django.shortcuts import  get_object_or_404
from .models import ChatRoom, Message
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
User = get_user_model()  # Always get custom user
from django.shortcuts import redirect
from UserApp.decorators import role_required
User = get_user_model()
from asgiref.sync import sync_to_async

async def receive(self, text_data):
    data = json.loads(text_data)
    message = data.get('message')

    if message:
        msg_obj = await sync_to_async(Message.objects.create)(
            room_id=self.room_id,
            sender_id=self.user.id,
            content=message
        )

        # send back to group
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'message': message,
                'id': msg_obj.id,
                'sender': self.user.username,
                'time': msg_obj.created_at.strftime("%H:%M"),
            }
        )

def send_private_message(request, room_id):
    """
    Send a message in a private room and save it to DB.
    """
    room = get_object_or_404(ChatRoom, id=room_id)

    # Security check
    if request.user not in room.participants.all():
        return JsonResponse({'error': 'forbidden'}, status=403)

    # Get message content
    content = request.POST.get('content', '').strip()
    if not content:
        return JsonResponse({'error': 'empty_message'}, status=400)

    # ✅ Save message to database
    message = Message.objects.create(
        room=room,
        sender=request.user,
        content=content
    )

    # ✅ Return message details
    return JsonResponse({
        'status': 'ok',
        'id': message.id,
        'sender_id': message.sender.id,
        'sender_first': message.sender.first_name or "",
        'sender_last': message.sender.last_name or "",
        'content': message.content,
        'time': message.created_at.strftime("%H:%M")
    })
def get_or_create_room(request, doctor_id):
    """Return JSON with the room id for a private conversation with doctor_id, creating it if necessary."""
    doctor = get_object_or_404(User, pk=doctor_id)
    if doctor == request.user:
        return JsonResponse({'error': 'cannot_create_with_self'}, status=400)

    room = ChatRoom.objects.filter(participants=request.user).filter(participants=doctor).filter(is_private=True).first()
    if not room:
        room = ChatRoom.objects.create(name=f"{request.user.first_name}_{doctor.first_name}_chat", is_private=True)
        room.participants.add(request.user, doctor)

    return JsonResponse({'room_id': room.id})

def get_or_create_private_room(request, doctor_id):
    """
    Retourne l'ID de la room privée entre l'utilisateur actuel et le docteur.
    Crée la room si elle n'existe pas encore.
    """
    doctor = get_object_or_404(User, pk=doctor_id)
    if doctor == request.user:
        return JsonResponse({'error': 'cannot_create_with_self'}, status=400)

    # Cherche une room privée existante avec les deux participants
    room = ChatRoom.objects.filter(is_private=True)\
        .filter(participants=request.user)\
        .filter(participants=doctor)\
        .first()

    if not room:
        room = ChatRoom.objects.create(
            name=f"{request.user.first_name}_{doctor.first_name}_chat",
            is_private=True
        )
        room.participants.add(request.user, doctor)

    # Récupère tous les messages existants
    messages = room.messages.all().order_by('created_at')
    messages_data = [
        {
            'id': msg.id,
            'sender_id': msg.sender.id,
            'sender_first': getattr(msg.sender, 'first_name', ''),
            'sender_last': getattr(msg.sender, 'last_name', ''),
            'content': msg.content,
            'time': msg.created_at.strftime("%H:%M"),
        } for msg in messages
    ]

    return JsonResponse({
        'room_id': room.id,
        'messages': messages_data
    })


def room_messages(request, room_id):
    """Return JSON list of messages for a room. Requires that request.user is participant."""
    room = get_object_or_404(ChatRoom, id=room_id)
    if request.user not in room.participants.all():
        return JsonResponse({'error': 'forbidden'}, status=403)

    msgs = []
    for m in room.messages.all().order_by('timestamp'):
        sender = m.sender
        msgs.append({
            'id': m.id,
            'sender_first': getattr(sender, 'first_name', ''),
            'sender_last': getattr(sender, 'last_name', ''),
            'content': m.content,
            'time': m.timestamp.strftime('%H:%M'),
        })

    return JsonResponse({'room_id': room.id, 'messages': msgs})


from django.contrib.auth.decorators import login_required

def my_chat_redirect(request):
    user = request.user  # already logged in

    # Find any doctor other than yourself
    other_doctor = User.objects.filter(role='Dr').exclude(pk=user.pk).first()
    if not other_doctor:
        # fallback: if no other doctor exists
        return redirect('Labapp:home')  # or any fallback page

    # Check if a private chat room already exists
    room = ChatRoom.objects.filter(
        is_private=True,
        participants=user
    ).filter(participants=other_doctor).first()

    # Create room if it doesn’t exist
    if not room:
        room = ChatRoom.objects.create(
            name=f"{user.first_name}_{other_doctor.first_name}_chat",
            is_private=True
        )
        room.participants.add(user, other_doctor)

    # Redirect to the actual room page
    return redirect('Labapp:chat_room', room_id=room.id)
def start_private_chat(request, doctor_id):
    """
    Start or get a private chat with another doctor.
    Already in a session, no login required.
    """
    user = request.user
    other_doctor = get_object_or_404(User, pk=doctor_id)

    # Try to find existing private room
    room = ChatRoom.objects.filter(is_private=True, participants=user)\
                           .filter(participants=other_doctor).first()
    
    if not room:
        room = ChatRoom.objects.create(
            name=f"{user.first_name}_{other_doctor.first_name}_chat",
            is_private=True
        )
        room.participants.add(user, other_doctor)

    return redirect('Labapp:chat_room', room_id=room.id)


def chat_room(request, room_id):
    room = get_object_or_404(ChatRoom, id=room_id)

    # S'assurer que l'utilisateur fait partie de la room
    if request.user not in room.participants.all():
        room.participants.add(request.user)

    # Récupérer TOUS les docteurs sauf l'utilisateur actuel
    doctors = User.objects.filter(role='doctor').exclude(pk=request.user.pk)

    return render(request, 'Front/labo/recherche/room.html', {
        'room': room,
        'messages': room.messages.all().order_by('created_at'),
        'doctors': doctors,
    })

def send_message(request, room_id):
    if request.method == 'POST':
        room = get_object_or_404(ChatRoom, id=room_id)

        # Security check
        if request.user not in room.participants.all():
            return JsonResponse({'error': 'forbidden'}, status=403)

        content = request.POST.get('content', '').strip()
        if not content:
            return JsonResponse({'error': 'empty_message'}, status=400)

        # ✅ Save to database
        message = Message.objects.create(
            room=room,
            sender=request.user,
            content=content
        )

        return JsonResponse({
            'status': 'saved',
            'id': message.id
        })
def notifications_analyses_terminees(request):
    """
    Retourne le nombre d'analyses terminées et une liste de détails.
    """
    analyses_terminees = Analyse.objects.filter(etat='terminee').order_by('-date_res')[:10]  # top 10 récentes
    data = {
        'count': analyses_terminees.count(),
        'analyses': [
            {
                'id': a.id,
                'echantillon_code': a.echantillon_code,
                'patient_id': a.patient_id,
                'date_res': a.date_res.strftime("%d/%m/%Y") if a.date_res else ''
            } for a in analyses_terminees
        ]
    }
    return JsonResponse(data)
def recherche_stats(request):
    type_data = Recherche.objects.values('type_recherche').annotate(count=Count('id'))
    etat_data = Recherche.objects.values('etat').annotate(count=Count('id'))
    budget_data = Recherche.objects.values('type_recherche').annotate(total_budget=Sum('budget'))

    context = {
        'total_recherches': Recherche.objects.count(),
        'total_budget': Recherche.objects.aggregate(total=Sum('budget'))['total'] or 0,
        'pourcentage_en_cours': round((Recherche.objects.filter(etat='En cours').count() / Recherche.objects.count() * 100) if Recherche.objects.count() else 0, 1),

        'type_labels': [d['type_recherche'] for d in type_data],
        'type_counts': [d['count'] for d in type_data],

        'etat_labels': [d['etat'] for d in etat_data],
        'etat_counts': [d['count'] for d in etat_data],

        'budget_labels': [d['type_recherche'] for d in budget_data],
        'budget_values': [d['total_budget'] or 0 for d in budget_data],
    }
    return render(request, 'Back/labo/recherches/statistiques.html', context)
  
def analyse_pdf(request, pk):
    analyse = Analyse.objects.get(pk=pk)
    
    # Exemple: créer un diagramme pour les statistiques
    valeurs = [analyse.valeur1, analyse.valeur2, analyse.valeur3]  # adapter selon ton modèle
    labels = ['Valeur 1', 'Valeur 2', 'Valeur 3']
    
    plt.figure(figsize=(6,4))
    plt.bar(labels, valeurs, color=['blue','green','orange'])
    plt.title('Statistiques de l\'analyse')
    
    # Convertir le graphique en image base64 pour HTML
    buffer = io.BytesIO()
    plt.savefig(buffer, format='png')
    buffer.seek(0)
    image_png = buffer.getvalue()
    graph = base64.b64encode(image_png).decode('utf-8')
    buffer.close()
    plt.close()
    
    # Passer l'image au template
    html = render_to_string('Front/labo/analyse/pdf_template.html', {'analyse': analyse, 'graph': graph})
    
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="analyse_{analyse.id}.pdf"'
    
    pisa_status = pisa.CreatePDF(html, dest=response)
    if pisa_status.err:
        return HttpResponse("Erreur lors de la génération du PDF")
    return response

def analyse_pdf(request, pk):
    analyse = Analyse.objects.get(pk=pk)
    html = render_to_string('Front/labo/analyse/pdf_template.html', {'analyse': analyse})
    
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="analyse_{analyse.id}.pdf"'
    
    pisa_status = pisa.CreatePDF(html, dest=response)
    if pisa_status.err:
        return HttpResponse("Erreur lors de la génération du PDF")
    return response
@role_required('doctor')
def home(request):
    analyses = Analyse.objects.all()
    # Get all users with role 'doctor', excluding the current user
    doctors = User.objects.filter(role='doctor').exclude(pk=request.user.pk)
    return render(request, 'Front/labo/index.html', {
        'analyses': analyses,
        'doctors': doctors
    })
def back(request):
    return render(request, 'Back/index.html')
# ----------------------------
# Recherche Views
# ----------------------------

class RechercheCreateView(CreateView):
    model = Recherche
    form_class = RechercheForm
    template_name = "Front/labo/recherche/formul.html"
    success_url = reverse_lazy('Labapp:home_html')


class RechercheUpdateView(UpdateView):
    model = Recherche
    form_class = RechercheForm
    template_name = "Front/labo/recherche/formul.html"
    success_url = reverse_lazy('Labapp:recherche_list')

    def form_valid(self, form):
        response = super().form_valid(form)
        self.request.session['updated_id'] = self.object.id
        return response

class RechercheListView(ListView):
    model = Recherche
    template_name = "Front/labo/recherche/list.html"
    context_object_name = "recherches"
    paginate_by = 12  # optional

    SORTABLE_FIELDS = ["nom_recherche", "date_deb", "date_fin", "etat", "type_recherche"]

    def get_queryset(self):
        queryset = Recherche.objects.all()

        # --- Search ---
        q = self.request.GET.get("q", "").strip()
        if q:
            queryset = queryset.filter(
                Q(nom_recherche__icontains=q) |
                Q(maladie__icontains=q) |
                Q(objectif__icontains=q) |
                Q(type_recherche__icontains=q) |
                Q(etat__icontains=q)
            )

        # --- Sort ---
        sort_by = self.request.GET.get("sort", "id")  # default
        if sort_by in self.SORTABLE_FIELDS or (sort_by.startswith("-") and sort_by[1:] in self.SORTABLE_FIELDS):
            queryset = queryset.order_by(sort_by)
        else:
            queryset = queryset.order_by("-id")  # fallback

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['q'] = self.request.GET.get("q", "")
        context['sort'] = self.request.GET.get("sort", "id")
        context['updated_id'] = self.request.session.pop('updated_id', None)
        return context
class RechercheDeleteView(DeleteView):
    model = Recherche
    template_name = "Front/labo/recherche/delete_confirm.html"
    success_url = reverse_lazy('Labapp:recherche_list')

# ----------------------------
# Analyse Views
# ----------------------------
class AnalyseCreateView(CreateView):
    model = Analyse
    form_class = AnalyseForm
    template_name = "Front/labo/analyse/formul.html"
    success_url = reverse_lazy('Labapp:analyse_list')

class AnalyseUpdateView(UpdateView):
    model = Analyse
    form_class = AnalyseForm
    template_name = "Front/labo/analyse/formul.html"
    success_url = reverse_lazy('Labapp:analyse_list')

    def form_valid(self, form):
        response = super().form_valid(form)
        self.request.session['updated_id'] = self.object.id  # <-- stocke l'id mis à jour
        return response

class AnalyseListView(ListView):
    model = Analyse
    template_name = "Front/labo/analyse/list.html"
    context_object_name = "analyses"
    paginate_by = 12  # optional

    SORTABLE_FIELDS = ["nom_analyse", "date_deb", "date_fin", "etat", "type_analyse"]

    def get_queryset(self):
        queryset = Analyse.objects.all()

        # --- Search ---
        q = self.request.GET.get("q", "").strip()
        if q:
            queryset = queryset.filter(
                Q(nom_analyse__icontains=q) |
                Q(objectif__icontains=q) |
                Q(type_analyse__icontains=q) |
                Q(etat__icontains=q)
            )

        # --- Sort ---
        sort_by = self.request.GET.get("sort", "id")
        if sort_by in self.SORTABLE_FIELDS or (sort_by.startswith("-") and sort_by[1:] in self.SORTABLE_FIELDS):
            queryset = queryset.order_by(sort_by)
        else:
            queryset = queryset.order_by("-id")  # fallback

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['q'] = self.request.GET.get("q", "")
        context['sort'] = self.request.GET.get("sort", "id")
        context['updated_id'] = self.request.session.pop('updated_id', None)
        return context
    
class AnalyseDeleteView(DeleteView):
    model = Analyse
    template_name = "Front/labo/analyse/delete_confirm.html"
    success_url = reverse_lazy('Labapp:analyse_list')

class BackRechercheUpdateView(UpdateView):
    model = Recherche
    form_class = RechercheForm
    template_name = "Back/labo/recherches/formul.html"  # back template
    success_url = reverse_lazy('Labapp:back_recherche_list')

    def form_valid(self, form):
        response = super().form_valid(form)
        self.request.session['updated_id'] = self.object.id
        return response



class BackAnalyseDeleteView(DeleteView):
    model = Analyse
    success_url = reverse_lazy('Labapp:back_analyse_list')

    def get(self, request, *args, **kwargs):
        # Redirect to list if someone tries GET
        return redirect(self.success_url)


# ----------------------------
class BackAnalyseListView(ListView):
    model = Analyse
    template_name = "Back/labo/analyses/list.html"
    context_object_name = "analyses"
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['updated_id'] = self.request.GET.get('updated', None)
        return context

class BackAnalyseUpdateView(UpdateView):
    model = Analyse
    form_class = AnalyseForm
    template_name = "Back/labo/analyses/list.html"  # Not actually used
    def form_valid(self, form):
        self.object = form.save()
        # redirect back to the list with ?updated=<id> so JS highlights row
        return redirect(f"{reverse_lazy('Labapp:back_analyse_list')}?updated={self.object.id}")
class BackRechercheListView(ListView):
    model = Recherche
    template_name = "Back/labo/recherches/list.html"
    context_object_name = "recherches"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # récupère l'id mis à jour pour le JS
        context['updated_id'] = self.request.GET.get('updated', None)
        return context


class BackRechercheUpdateView(UpdateView):
    model = Recherche
    form_class = RechercheForm
    template_name = "Back/labo/recherches/list.html"  # même template que la liste

    def form_valid(self, form):
        self.object = form.save()
        # redirect back to the list with ?updated=<id> for JS highlight
        return redirect(f"{reverse_lazy('Labapp:back_recherche_list')}?updated={self.object.id}")


class BackRechercheDeleteView(DeleteView):
    model = Recherche
    success_url = reverse_lazy('Labapp:back_recherche_list')

    def get(self, request, *args, **kwargs):
        # Empêche GET pour delete
        return redirect(self.success_url)
def map_view(request):
    return render(request, 'Front/labo/recherche/map.html')
from django.urls import reverse_lazy

