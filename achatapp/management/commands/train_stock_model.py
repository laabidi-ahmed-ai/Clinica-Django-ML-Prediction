"""
Commande Django pour entraîner le modèle ML de prédiction de rupture de stock
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
import pandas as pd
import numpy as np
from achatapp.models import Produit, Commande
from achatapp.ml.stock_predictor import StockPredictor, get_predictor


class Command(BaseCommand):
    help = 'Entraîne le modèle ML Random Forest pour prédire les ruptures de stock'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=90,
            help='Nombre de jours de données historiques à utiliser (défaut: 90)'
        )

    def handle(self, *args, **options):
        days = options['days']
        
        self.stdout.write('Preparation des donnees pour l\'entrainement du modele ML...')
        
        # Récupérer tous les produits
        produits = Produit.objects.all()
        
        if not produits.exists():
            self.stdout.write(self.style.WARNING('Aucun produit trouvé.'))
            return
        
        # Préparer les données d'entraînement
        training_data = []
        
        for produit in produits:
            self.stdout.write(f'Traitement du produit: {produit.nom}')
            
            # Calculer les statistiques des ventes
            end_date = timezone.now()
            start_date = end_date - timedelta(days=days)
            
            orders = Commande.objects.filter(
                produit=produit,
                statut='acceptee',
                date_creation__gte=start_date,
                date_creation__lte=end_date
            )
            
            if orders.count() < 5:
                self.stdout.write(self.style.WARNING(f'  Pas assez de commandes ({orders.count()}) pour ce produit'))
                continue
            
            # Calculer les features
            total_sold = sum(order.quantite for order in orders)
            avg_daily_sales = total_sold / days
            
            # Tendance des 7 derniers jours
            last_7_days = end_date - timedelta(days=7)
            recent_orders = orders.filter(date_creation__gte=last_7_days)
            recent_sold = sum(order.quantite for order in recent_orders)
            trend_7days = recent_sold / 7 if recent_orders.exists() else avg_daily_sales
            
            # Variance des ventes (calculée sur des fenêtres de 7 jours)
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
            
            sales_variance = np.var(sales_by_week) if len(sales_by_week) > 1 else 0
            
            # Pour chaque point dans le temps (simulation), calculer quand la rupture aurait eu lieu
            # On simule différents scénarios basés sur les données historiques
            
            # Scénario 1: Stock initial élevé
            initial_stock_scenarios = [50, 100, 200, 500]
            
            for initial_stock in initial_stock_scenarios:
                # Simuler le stock au fil du temps
                current_stock = initial_stock
                days_until_out = 0
                
                # Parcourir les commandes dans l'ordre chronologique
                ordered_orders = orders.order_by('date_creation')
                
                for order in ordered_orders:
                    if current_stock <= 0:
                        break
                    current_stock -= order.quantite
                    days_until_out += 1
                
                # Si on n'a pas épuisé le stock, estimer
                if current_stock > 0 and avg_daily_sales > 0:
                    days_until_out += int(current_stock / avg_daily_sales)
                
                # Ajouter les données d'entraînement
                if days_until_out > 0 and days_until_out <= 365:  # Limiter à 1 an
                    training_data.append({
                        'current_stock': initial_stock,
                        'avg_daily_sales': avg_daily_sales,
                        'category': produit.category,
                        'prix_vente': float(produit.prix_vente),
                        'trend_7days': trend_7days,
                        'sales_variance': sales_variance,
                        'days_until_out_of_stock': days_until_out
                    })
        
        if not training_data:
            self.stdout.write(
                self.style.ERROR('Aucune donnee d\'entrainement generee. Verifiez que des commandes existent.')
            )
            return
        
        # Créer un DataFrame
        df = pd.DataFrame(training_data)
        
        self.stdout.write(f'\n[OK] {len(df)} echantillons d\'entrainement prepares')
        self.stdout.write(f'  Colonnes: {list(df.columns)}')
        
        # Entraîner le modèle
        self.stdout.write('\nEntrainement du modele Random Forest...')
        
        predictor = get_predictor()
        success = predictor.train(df)
        
        if success:
            self.stdout.write(
                self.style.SUCCESS('\n[SUCCES] Modele ML entraine et sauvegarde avec succes!')
            )
            self.stdout.write('  Le modele est maintenant disponible pour les predictions.')
        else:
            self.stdout.write(
                self.style.ERROR('\n[ERREUR] Erreur lors de l\'entrainement du modele.')
            )
            self.stdout.write('  Les predictions utiliseront la methode simple de fallback.')

