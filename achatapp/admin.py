from django.contrib import admin
from django.utils.html import format_html
from django.contrib import messages
from django.urls import reverse
from django.shortcuts import get_object_or_404, redirect
from django.utils.safestring import mark_safe
from .models import Produit, Commande, Coupon


@admin.register(Produit)
class ProduitAdmin(admin.ModelAdmin):
    list_display = ('get_image', 'nom', 'category', 'prix_achat', 'prix_vente', 'quantite', 'date_ajout')
    list_editable = ('prix_achat', 'prix_vente', 'quantite', 'category')
    search_fields = ('nom', 'description')
    list_filter = ('category', 'date_ajout')
    fields = ('nom', 'description', 'category', 'prix_achat', 'prix_vente', 'quantite', 'image')

    def get_image(self, obj):
        if obj.image:
            return format_html(
                "<img src='{}' width='50' height='50' style='object-fit:cover;border-radius:5px;'/>",
                obj.image.url
            )
        return "(No Image)"
    get_image.short_description = 'Image'


@admin.register(Commande)
class CommandeAdmin(admin.ModelAdmin):
    list_display = ('id', 'produit', 'quantite', 'get_total', 'statut', 'nom_client', 'prenom_client', 'date_creation', 'commande_actions')
    list_filter = ('statut', 'date_creation')
    search_fields = ('produit__nom', 'nom_client', 'prenom_client', 'email_client', 'telephone_client')
    readonly_fields = ('date_creation', 'date_modification', 'get_total')
    list_editable = ()
    actions = []  # Disable bulk actions to avoid conflicts
    
    fieldsets = (
        ('Product Information', {
            'fields': ('produit', 'quantite', 'get_total')
        }),
        ('Customer Information', {
            'fields': ('nom_client', 'prenom_client', 'email_client', 'telephone_client', 'adresse_client')
        }),
        ('Status', {
            'fields': ('statut', 'date_creation', 'date_modification')
        }),
    )
    
    def get_total(self, obj):
        return f"{obj.total} DT"
    get_total.short_description = 'Total'
    
    @admin.display(description='Actions')
    def commande_actions(self, obj):
        if obj is None or not isinstance(obj, Commande):
            return '-'
        if obj.statut == 'en_attente':
            accept_url = reverse('admin:achatapp_commande_accept', args=[obj.pk])
            refuse_url = reverse('admin:achatapp_commande_refuse', args=[obj.pk])
            return format_html(
                '<a class="button" href="{}" style="background-color: #28a745; color: white; padding: 5px 10px; text-decoration: none; border-radius: 3px; margin-right: 5px;">Accept</a> '
                '<a class="button" href="{}" style="background-color: #dc3545; color: white; padding: 5px 10px; text-decoration: none; border-radius: 3px;">Reject</a>',
                accept_url,
                refuse_url
            )
        return format_html('<span style="color: #666;">{}</span>', obj.get_statut_display())
    
    def get_urls(self):
        from django.urls import path
        urls = super().get_urls()
        custom_urls = [
            path('<int:commande_id>/accept/', self.accept_commande, name='achatapp_commande_accept'),
            path('<int:commande_id>/refuse/', self.refuse_commande, name='achatapp_commande_refuse'),
        ]
        return custom_urls + urls
    
    def accept_commande(self, request, commande_id):
        commande = get_object_or_404(Commande, id=commande_id)
        try:
            commande.accepter()
            messages.success(request, f'Order #{commande.id} accepted successfully. Stock updated.')
        except Exception as e:
            messages.error(request, f'Error: {str(e)}')
        return redirect('admin:achatapp_commande_changelist')
    
    def refuse_commande(self, request, commande_id):
        commande = get_object_or_404(Commande, id=commande_id)
        try:
            commande.refuser()
            messages.success(request, f'Order #{commande.id} rejected.')
        except Exception as e:
            messages.error(request, f'Error: {str(e)}')
        return redirect('admin:achatapp_commande_changelist')


@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    """Admin pour les coupons - montre analytics et statistiques"""
    list_display = ('code', 'discount_percent', 'current_uses', 'max_uses', 
                   'is_active', 'generated_from_quiz', 'created_at', 'expires_at', 'usage_rate')
    list_filter = ('is_active', 'generated_from_quiz', 'created_at')
    search_fields = ('code',)
    readonly_fields = ('code', 'created_at', 'current_uses', 'usage_rate_display')
    
    fieldsets = (
        ('Informations du Coupon', {
            'fields': ('code', 'discount_percent', 'is_active')
        }),
        ('Utilisation', {
            'fields': ('max_uses', 'current_uses', 'usage_rate_display', 'used_by')
        }),
        ('Analytics', {
            'fields': ('generated_from_quiz', 'quiz_score', 'created_at', 'expires_at')
        }),
    )
    
    def usage_rate(self, obj):
        """Calcule le taux d'utilisation"""
        if obj.max_uses > 0:
            rate = (obj.current_uses / obj.max_uses) * 100
            color = 'green' if rate < 50 else 'orange' if rate < 100 else 'red'
            return format_html(
                '<span style="color: {};">{:.1f}%</span>',
                color, rate
            )
        return 'N/A'
    usage_rate.short_description = 'Taux d\'utilisation'
    
    def usage_rate_display(self, obj):
        """Affiche le taux d'utilisation dans les détails"""
        if obj.max_uses > 0:
            return f"{obj.current_uses}/{obj.max_uses} ({self.usage_rate(obj)})"
        return f"{obj.current_uses} utilisations"
    usage_rate_display.short_description = 'Taux d\'utilisation'






