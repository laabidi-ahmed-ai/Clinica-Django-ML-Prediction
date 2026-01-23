from django.contrib import admin
from .models import Recherche, Analyse

# ----------------------------


# ----------------------------
# Recherche Admin
# ----------------------------
class RechercheAdmin(admin.ModelAdmin):
    list_display = ('nom_recherche', 'maladie', 'type_recherche', 'etat', 'date_deb', 'date_fin', 'responsable', 'equipement')
    list_filter = ('type_recherche', 'etat', 'responsable')
    search_fields = ('nom_recherche', 'maladie', 'objectif')
    date_hierarchy = 'date_deb'
    ordering = ('-date_deb',)

admin.site.register(Recherche, RechercheAdmin)

# ----------------------------
# Analyse Admin
# ----------------------------
class AnalyseAdmin(admin.ModelAdmin):
    list_display = ('echantillon_code', 'type', 'etat', 'date_prelevement', 'date_res', 'responsable_analyse', 'valide_par', 'cout')
    list_filter = ('type', 'etat', 'responsable_analyse', 'valide_par')
    search_fields = ('echantillon_code', 'patient_id', 'technique_utilisee')
    date_hierarchy = 'date_prelevement'
    ordering = ('-date_prelevement',)

admin.site.register(Analyse, AnalyseAdmin)
