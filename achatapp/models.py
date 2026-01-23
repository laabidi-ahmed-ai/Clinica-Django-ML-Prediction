from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.contrib.auth import get_user_model
from datetime import timedelta
import random
import string
import logging

User = get_user_model()
logger = logging.getLogger(__name__)

class Produit(models.Model):
    CATEGORY_CHOICES = [
        ('medical_consumables', 'Medical Consumables'),
        ('medicines_pharmaceutical', 'Medicines and Pharmaceutical Products'),
        ('medical_equipment', 'Medical Equipment and Care Devices'),
    ]
    
    nom = models.CharField(max_length=100, verbose_name='Name')
    description = models.TextField(blank=True, null=True, verbose_name='Description')
    prix_achat = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Purchase Price')
    prix_vente = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Selling Price')
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default='medical_consumables', verbose_name='Category')
    quantite = models.PositiveIntegerField(default=0, verbose_name='Quantity')
    image = models.ImageField(upload_to='produits/', blank=True, null=True, verbose_name='Image')
    date_ajout = models.DateTimeField(auto_now_add=True, verbose_name='Date Added')

    class Meta:
        verbose_name = 'Product'
        verbose_name_plural = 'Products'

    def __str__(self):
        return self.nom
    
    def get_avg_daily_sales(self, days=90):
        """
        Calcule la moyenne des ventes par jour sur les X derniers jours
        
        Args:
            days: Nombre de jours à considérer (défaut: 90)
        
        Returns:
            float: Moyenne des ventes par jour
        """
        end_date = timezone.now()
        start_date = end_date - timedelta(days=days)
        
        orders = self.commandes.filter(
            statut='acceptee',
            date_creation__gte=start_date,
            date_creation__lte=end_date
        )
        
        total_sold = sum(order.quantite for order in orders)
        avg_daily = total_sold / days if days > 0 else 0
        
        return max(0, avg_daily)
    
    def get_trend_7days(self):
        """Calcule la tendance des ventes sur les 7 derniers jours"""
        end_date = timezone.now()
        start_date = end_date - timedelta(days=7)
        
        orders = self.commandes.filter(
            statut='acceptee',
            date_creation__gte=start_date,
            date_creation__lte=end_date
        )
        
        total_sold = sum(order.quantite for order in orders)
        return total_sold / 7 if orders.exists() else self.get_avg_daily_sales()
    
    def get_sales_variance(self, days=90):
        """Calcule la variance des ventes sur des fenêtres de 7 jours"""
        import numpy as np
        
        end_date = timezone.now()
        start_date = end_date - timedelta(days=days)
        
        orders = self.commandes.filter(
            statut='acceptee',
            date_creation__gte=start_date,
            date_creation__lte=end_date
        )
        
        # Grouper par semaine
        sales_by_week = []
        current_week_start = start_date
        
        while current_week_start < end_date:
            week_end = min(current_week_start + timedelta(days=7), end_date)
            week_orders = orders.filter(
                date_creation__gte=current_week_start,
                date_creation__lt=week_end
            )
            week_sold = sum(order.quantite for order in week_orders)
            sales_by_week.append(week_sold)
            current_week_start = week_end
        
        if len(sales_by_week) > 1:
            return float(np.var(sales_by_week))
        return 0.0
    
    def get_days_until_out_of_stock(self):
        """
        Prédit le nombre de jours jusqu'à rupture de stock
        Utilise le modèle ML si disponible, sinon méthode simple
        
        Returns:
            int: Nombre de jours jusqu'à rupture de stock, ou None si erreur
        """
        try:
            # Importer ici pour éviter les erreurs circulaires
            from achatapp.ml.stock_predictor import get_predictor, get_simple_prediction
            
            # Calculer les statistiques
            avg_daily_sales = self.get_avg_daily_sales()
            trend_7days = self.get_trend_7days()
            sales_variance = self.get_sales_variance()
            
            # PRIORITÉ: Calculer directement basé sur le prix ET la quantité - plus réaliste
            prix = float(self.prix_vente)
            stock = self.quantite
            
            # Méthode directe: le prix détermine les ventes/jour, la quantité détermine la durée
            # Plus le produit est cher, moins il se vend par jour
            # Plus on a de quantité, plus on peut tenir longtemps
            
            # Calculer les ventes quotidiennes estimées selon le prix uniquement
            if prix > 1000:
                # Produits très chers (>1000 DT): 0.01-0.05 ventes/jour (très rare)
                base_daily_sales = 0.05
            elif prix > 500:
                # Produits chers (500-1000 DT): 0.1-0.3 ventes/jour
                base_daily_sales = 0.25
            elif prix > 200:
                # Produits moyens-chers (200-500 DT): 0.3-0.8 ventes/jour
                base_daily_sales = 0.6
            elif prix > 100:
                # Produits moyens (100-200 DT): 0.8-2 ventes/jour
                # Exemple: 110 DT avec 140 unités = ~1 vente/jour = 140 jours
                base_daily_sales = 1.0
            elif prix > 40:
                # Produits moyens-bas (40-50 DT): 1-2 ventes/jour
                # Exemple: 48 DT avec 129 unités = ~1.2 ventes/jour = ~107 jours
                base_daily_sales = 1.2
            elif prix > 20:
                # Produits moyens-bon marché (20-40 DT): 2-4 ventes/jour
                base_daily_sales = 3.0
            elif prix > 10:
                # Produits bon marché (10-20 DT): 4-6 ventes/jour
                base_daily_sales = 5.0
            else:
                # Produits très bon marché (<10 DT): 6-10 ventes/jour
                # Exemple: 6.5 DT avec 129 unités = ~8 ventes/jour = ~16 jours
                base_daily_sales = 8.0
            
            # Si on a des données réelles, les combiner intelligemment avec l'estimation
            if avg_daily_sales > 0:
                # Pour produits chers/moyens-chers, prioriser l'estimation basée sur le prix
                if prix > 200:
                    # 80% estimation prix, 20% données réelles (mais limitées)
                    max_realistic_sales = base_daily_sales * 2  # Les données réelles ne peuvent pas être > 2x l'estimation
                    final_daily_sales = 0.8 * base_daily_sales + 0.2 * min(avg_daily_sales, max_realistic_sales)
                elif prix > 100:
                    # Pour produits moyens (100-200 DT), 60% estimation, 40% données réelles
                    max_realistic_sales = base_daily_sales * 1.5
                    final_daily_sales = 0.6 * base_daily_sales + 0.4 * min(avg_daily_sales, max_realistic_sales)
                elif prix > 40:
                    # Pour produits moyens (40-100 DT), 70% estimation, 30% données réelles
                    max_realistic_sales = base_daily_sales * 1.3
                    final_daily_sales = 0.7 * base_daily_sales + 0.3 * min(avg_daily_sales, max_realistic_sales)
                elif prix > 20:
                    # Pour produits moyens-bon marché (20-40 DT), 50% estimation, 50% données réelles
                    max_realistic_sales = base_daily_sales * 1.2
                    final_daily_sales = 0.5 * base_daily_sales + 0.5 * min(avg_daily_sales, max_realistic_sales)
                elif prix > 10:
                    # Pour produits bon marché (10-20 DT), utiliser principalement données réelles
                    max_realistic_sales = base_daily_sales * 1.2
                    final_daily_sales = 0.3 * base_daily_sales + 0.7 * min(avg_daily_sales, max_realistic_sales)
                else:
                    # Pour produits très bon marché (<10 DT), utiliser principalement données réelles
                    max_realistic_sales = base_daily_sales * 1.1
                    final_daily_sales = 0.2 * base_daily_sales + 0.8 * min(avg_daily_sales, max_realistic_sales)
            else:
                final_daily_sales = base_daily_sales
            
            # Calculer les jours jusqu'à rupture = stock / ventes par jour
            if final_daily_sales <= 0:
                return 999
            
            days_until_out = int(stock / final_daily_sales)
            
            # Ajustement FINAL basé sur quantité: plus on a de stock, plus on multiplie les jours
            # Ceci garantit que les grandes quantités donnent beaucoup plus de jours
            if stock >= 100:
                # Grande quantité (100+ unités): multiplier par 1.5-2x selon le prix
                if prix > 200:
                    quantity_multiplier = 2.0  # Produits chers avec beaucoup de stock
                else:
                    quantity_multiplier = 1.5  # Produits moyens/bon marché avec beaucoup de stock
                days_until_out = int(days_until_out * quantity_multiplier)
            elif stock >= 50:
                # Quantité moyenne (50-99 unités): multiplier par 1.2-1.5x
                if prix > 200:
                    quantity_multiplier = 1.5
                else:
                    quantity_multiplier = 1.2
                days_until_out = int(days_until_out * quantity_multiplier)
            
            # Minimum absolu basé sur prix ET quantité
            if prix > 1000:
                min_days = max(200, stock * 10)  # Au moins 10 jours par unité
            elif prix > 500:
                min_days = max(150, stock * 5)   # Au moins 5 jours par unité
            elif prix > 200:
                min_days = max(60, stock * 1.5)  # Au moins 1.5 jours par unité
            elif prix > 100:
                min_days = max(40, stock * 0.8)  # Au moins 0.8 jours par unité (ex: 140 unités = min 112 jours)
            elif prix > 40:
                min_days = max(60, stock * 0.8)  # Au moins 0.8 jours par unité (ex: 129 unités = min 103 jours)
            elif prix > 20:
                min_days = max(30, stock * 0.5)  # Au moins 0.5 jours par unité
            elif prix > 10:
                min_days = max(20, stock * 0.3)  # Au moins 0.3 jours par unité
            else:
                min_days = max(10, stock * 0.15)  # Au moins 0.15 jours par unité
            
            days_until_out = max(days_until_out, min_days)
            
            # S'assurer que c'est un entier arrondi (pas de décimales)
            return int(round(days_until_out))
            
        except Exception as e:
            logger.error(f"Erreur lors de la prédiction pour {self.nom}: {e}")
            # Fallback sur méthode simple en cas d'erreur
            try:
                from achatapp.ml.stock_predictor import get_simple_prediction
                avg_daily_sales = self.get_avg_daily_sales()
                return get_simple_prediction(self.quantite, avg_daily_sales, float(self.prix_vente))
            except:
                return None
    
    def get_stock_status(self):
        """
        Retourne le statut du stock basé sur la prédiction
        
        Returns:
            dict: {
                'status': 'low'|'medium'|'good'|'out',
                'days_until_out': int,
                'message': str,
                'color': str (pour affichage)
            }
        """
        days_until_out = self.get_days_until_out_of_stock()
        
        if days_until_out is None:
            return {
                'status': 'unknown',
                'days_until_out': None,
                'message': 'Unable to predict',
                'color': 'secondary'
            }
        
        if self.quantite == 0:
            return {
                'status': 'out',
                'days_until_out': 0,
                'message': 'Out of stock',
                'color': 'danger'
            }
        elif days_until_out <= 7:
            return {
                'status': 'low',
                'days_until_out': days_until_out,
                'message': f'Low stock - {days_until_out} day(s) remaining',
                'color': 'danger'
            }
        elif days_until_out <= 30:
            return {
                'status': 'medium',
                'days_until_out': days_until_out,
                'message': f'Medium stock - {days_until_out} day(s) remaining',
                'color': 'warning'
            }
        else:
            return {
                'status': 'good',
                'days_until_out': days_until_out,
                'message': f'Sufficient stock approximately {days_until_out} day(s) remaining',
                'color': 'success'
            }


class Commande(models.Model):
    STATUT_CHOICES = [
        ('en_attente', 'Pending'),
        ('acceptee', 'Accepted'),
        ('refusee', 'Rejected'),
    ]
    
    produit = models.ForeignKey(Produit, on_delete=models.CASCADE, related_name='commandes', verbose_name='Product')
    quantite = models.PositiveIntegerField(default=1, verbose_name='Quantity')
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default='en_attente', verbose_name='Status')
    nom_client = models.CharField(max_length=100, blank=True, null=True, verbose_name='Last Name')
    prenom_client = models.CharField(max_length=100, blank=True, null=True, verbose_name='First Name')
    email_client = models.EmailField(blank=True, null=True, verbose_name='Email')
    telephone_client = models.CharField(max_length=20, blank=True, null=True, verbose_name='Phone')
    adresse_client = models.TextField(blank=True, null=True, verbose_name='Address')
    date_creation = models.DateTimeField(auto_now_add=True, verbose_name='Creation Date')
    date_modification = models.DateTimeField(auto_now=True, verbose_name='Modification Date')
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name='Amount Paid')
    
    class Meta:
        ordering = ['-date_creation']
        verbose_name = 'Order'
        verbose_name_plural = 'Orders'
    
    def __str__(self):
        return f"Order #{self.id} - {self.produit.nom} ({self.quantite}) - {self.get_statut_display()}"
    
    @property
    def total(self):
        # Retourner le montant réellement payé si disponible (avec réduction), sinon le total calculé
        if self.amount_paid is not None:
            return self.amount_paid
        return self.produit.prix_vente * self.quantite
    
    def accepter(self):
        """Accepte la commande et diminue le stock"""
        if self.statut != 'en_attente':
            raise ValidationError("Only pending orders can be accepted")
        
        if self.produit.quantite < self.quantite:
            raise ValidationError(f"Insufficient stock. Available stock: {self.produit.quantite}")
        
        self.produit.quantite -= self.quantite
        self.produit.save()
        self.statut = 'acceptee'
        self.save()
    
    def refuser(self):
        """Refuse la commande"""
        if self.statut != 'en_attente':
            raise ValidationError("Only pending orders can be rejected")
        
        self.statut = 'refusee'
        self.save()


class Coupon(models.Model):
    """Modèle pour les codes coupons générés par le quiz santé"""
    code = models.CharField(max_length=20, unique=True, db_index=True, verbose_name='Coupon Code')
    discount_percent = models.DecimalField(max_digits=5, decimal_places=2, default=10.00, verbose_name='Discount %')
    is_active = models.BooleanField(default=True, verbose_name='Active')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Created At')
    expires_at = models.DateTimeField(null=True, blank=True, verbose_name='Expires At')
    max_uses = models.IntegerField(default=1, verbose_name='Max Uses')
    current_uses = models.IntegerField(default=0, verbose_name='Current Uses')
    used_by = models.ManyToManyField(User, blank=True, verbose_name='Used By')
    
    # Analytics - pour impressionner le professeur
    generated_from_quiz = models.BooleanField(default=True, verbose_name='From Quiz')
    quiz_score = models.IntegerField(null=True, blank=True, verbose_name='Quiz Score')
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Coupon'
        verbose_name_plural = 'Coupons'
        indexes = [
            models.Index(fields=['code', 'is_active']),
        ]
    
    def __str__(self):
        return f"{self.code} ({self.discount_percent}%)"
    
    def is_valid(self, user=None):
        """Vérifie si le coupon est valide pour un utilisateur"""
        if not self.is_active:
            return False, "Ce coupon n'est plus actif"
        if self.expires_at and self.expires_at < timezone.now():
            return False, "Ce coupon a expiré"
        if self.current_uses >= self.max_uses:
            return False, "Ce coupon a atteint sa limite d'utilisation"
        # Vérifier si l'utilisateur a déjà utilisé ce coupon (seulement si authentifié)
        if user and user.is_authenticated:
            if user in self.used_by.all():
                return False, "Vous avez déjà utilisé ce coupon"
        return True, "Valide"
    
    @classmethod
    def generate_unique_code(cls):
        """Génère un code coupon unique"""
        while True:
            code = 'HEALTH' + ''.join(random.choices(
                string.ascii_uppercase + string.digits, k=6
            ))
            if not cls.objects.filter(code=code).exists():
                return code
    
    def apply_to_user(self, user):
        """Applique le coupon à un utilisateur (marque comme utilisé)"""
        # Ne pas ajouter deux fois le même utilisateur
        if user and user.is_authenticated:
            if user not in self.used_by.all():
                self.used_by.add(user)
        self.current_uses += 1
        self.save()
