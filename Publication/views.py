from django.shortcuts import render,redirect
from django.http import HttpResponse
from.models import Publication
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView,View
from django.urls import reverse_lazy
from.forms import PublicationForm
from django.shortcuts import render
from django.contrib import messages

# Create your views here.
from django.db.models import Q
from django.utils.timezone import make_aware
from datetime import datetime
class PublicationListView(ListView):
    model = Publication
    context_object_name = 'publications'
    template_name = 'Back/Publication/publication_list.html'
    paginate_by = 10

    def get_queryset(self):
        queryset = Publication.objects.all()

        # --- GET params ---
        search_query = self.request.GET.get('search', "").strip()
        sort_by = self.request.GET.get('sort', "")
        date_filter = self.request.GET.get('date', "")

        # 🔍 SEARCH
        if search_query:
            queryset = queryset.filter(
                Q(title__icontains=search_query) |
                Q(description__icontains=search_query)
            )

        # 📅 DATE FILTER (date_pub)
        if date_filter:
            try:
                date_obj = datetime.strptime(date_filter, "%Y-%m-%d")
                queryset = queryset.filter(date_pub__date=date_obj.date())
            except:
                pass

        # ↕ SORTING
        if sort_by == "date_asc":
            queryset = queryset.order_by("date_pub")
        elif sort_by == "date_desc":
            queryset = queryset.order_by("-date_pub")
        elif sort_by == "deadline_asc":
            queryset = queryset.order_by("deadline")
        elif sort_by == "deadline_desc":
            queryset = queryset.order_by("-deadline")
        else:
            queryset = queryset.order_by("-date_pub")  # Default: newest first

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # On repasse les valeurs au template pour garder les champs remplis
        context["search_query"] = self.request.GET.get("search", "")
        context["sort_by"] = self.request.GET.get("sort", "")
        context["date_filter"] = self.request.GET.get("date", "")

        return context


class PublicationDetailView(DetailView):
    model = Publication
    template_name = 'Back/Publication/publication_detail.html'
    context_object_name = 'publication'

class PublicationCreateView(CreateView):
    model = Publication
    form_class = PublicationForm
    template_name = 'Back/Publication/publication_form.html'
    
    def get_success_url(self):
        messages.success(self.request, 'Publication créée avec succès!')
        return reverse_lazy('publication:publication_list')


class PublicationUpdateView(UpdateView):
    model = Publication
    form_class = PublicationForm
    template_name = 'Back/Publication/publication_form.html'
    success_url = reverse_lazy('publication:publication_list')

class PublicationDeleteView(DeleteView):
    model = Publication
    success_url = reverse_lazy('publication:publication_list')
    
    # Pas besoin de template_name car on gère avec la modal
    def get(self, request, *args, **kwargs):
        # Rediriger vers la liste si quelqu'un accède directement à l'URL GET
        return redirect('publication:publication_list')
    
"""
class PublicationDeleteView(View):
    def post(self, request, pk):
        publication = Publication.objects.get(pk=pk)
        title = publication.title
        publication.delete()
        messages.success(request, f'La publication "{title}" a été supprimée avec succès.')
        return redirect('publication:publication_list')
"""


def home(request):
    return render(request, 'Front/home.html')