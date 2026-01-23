"""
Commande Django pour générer des données historiques de commandes
pour l'entraînement du modèle ML de prédiction de rupture de stock
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
import random
from decimal import Decimal
from achatapp.models import Produit, Commande


class Command(BaseCommand):
    help = 'Génère des données historiques de commandes pour l\'entraînement du modèle ML'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=90,
            help='Nombre de jours de données historiques à générer (défaut: 90)'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force la régénération même si des données existent déjà'
        )

    def handle(self, *args, **options):
        days = options['days']
        force = options['force']
        
        self.stdout.write(f'Génération de données historiques pour {days} jours...')
        
        # Récupérer tous les produits
        produits = Produit.objects.all()
        
        if not produits.exists():
            self.stdout.write(self.style.WARNING('Aucun produit trouvé. Créez d\'abord des produits.'))
            return
        
        # Statistiques
        total_generated = 0
        
        for produit in produits:
            self.stdout.write(f'\nTraitement du produit: {produit.nom}')
            
            # Calculer la moyenne des ventes par jour (basée sur les commandes existantes)
            existing_orders = Commande.objects.filter(
                produit=produit,
                statut='acceptee'
            )
            
            # Si des commandes existent déjà et qu'on ne force pas, utiliser les données réelles
            if existing_orders.exists() and not force:
                self.stdout.write(f'  Des commandes existent déjà pour ce produit. Utilisez --force pour régénérer.')
                continue
            
            # Générer des commandes historiques
            generated = self.generate_historical_orders_for_product(produit, days)
            total_generated += generated
            
            self.stdout.write(self.style.SUCCESS(f'  {generated} commandes générées'))
        
        self.stdout.write(
            self.style.SUCCESS(
                f'\n[OK] Generation terminee! {total_generated} commandes historiques generees au total.'
            )
        )
        self.stdout.write(
            self.style.WARNING(
                '\n[IMPORTANT] Executez maintenant: python manage.py train_stock_model'
            )
        )

    def generate_historical_orders_for_product(self, produit, days):
        """Génère des commandes historiques pour un produit donné"""
        generated_count = 0
        end_date = timezone.now()
        start_date = end_date - timedelta(days=days)
        
        # Paramètres pour générer des données réalistes
        # Basés sur le type de produit et le prix
        base_daily_rate = self.get_base_daily_rate(produit)
        
        # Générer une commande par jour (en moyenne)
        current_date = start_date
        
        while current_date <= end_date:
            # Probabilité d'avoir une commande ce jour (basée sur le taux quotidien)
            # Plus le taux est bas, moins il y a de chance d'avoir une commande
            daily_rate = base_daily_rate
            prob_commande = min(0.9, daily_rate / 2.0)  # Max 90% de chance
            
            if random.random() < prob_commande:
                # Nombre de commandes ce jour (peut varier)
                num_orders_today = random.choices(
                    [1, 2, 3],
                    weights=[0.7, 0.25, 0.05]  # Plus probable d'avoir 1 commande
                )[0]
                
                for _ in range(num_orders_today):
                    # Générer une quantité réaliste
                    max_quantity = min(produit.quantite + 50, 20)  # Ne pas exagérer
                    quantity = random.randint(1, max(1, max_quantity))
                    
                    # Déterminer si la commande sera acceptée (90% acceptées historiquement)
                    status = 'acceptee' if random.random() < 0.9 else 'refusee'
                    
                    # Créer la commande avec date aléatoire dans la journée
                    order_date = current_date + timedelta(
                        hours=random.randint(8, 20),
                        minutes=random.randint(0, 59)
                    )
                    
                    # Calculer le stock au moment de la commande (approximation)
                    # Pour simplifier, on suppose un stock initial élevé
                    # En réalité, cela devrait être calculé dynamiquement
                    
                    order = Commande.objects.create(
                        produit=produit,
                        quantite=quantity,
                        statut=status,
                        nom_client=f'Client_{random.randint(1000, 9999)}',
                        prenom_client=f'Prénom_{random.randint(1, 100)}',
                        email_client=f'client{random.randint(100, 999)}@example.com',
                        telephone_client=f'+216{random.randint(10000000, 99999999)}',
                        adresse_client='Adresse générée automatiquement',
                        date_creation=order_date,
                        date_modification=order_date,
                        amount_paid=Decimal(str(produit.prix_vente * quantity)).quantize(Decimal('0.01'))
                    )
                    
                    # Si la commande est acceptée, mettre à jour le stock du produit
                    # (pour simuler l'historique, on ne modifie pas le stock actuel)
                    # On le fait juste pour calculer les statistiques
                    
                    generated_count += 1
            
            # Passer au jour suivant
            current_date += timedelta(days=1)
        
        return generated_count

    def get_base_daily_rate(self, produit):
        """Calcule un taux de vente quotidien de base pour un produit"""
        # Basé sur la catégorie et le prix
        category_rates = {
            'medical_consumables': 3.0,  # Ventes plus fréquentes (produits jetables)
            'medicines_pharmaceutical': 2.0,  # Ventes moyennes
            'medical_equipment': 0.2,  # Ventes moins fréquentes (équipements durables)
        }
        
        base_rate = category_rates.get(produit.category, 1.0)
        
        # Ajuster selon le prix (formule inverse - produits plus chers = moins de ventes)
        prix = float(produit.prix_vente)
        
        # Formule plus réaliste : plus le prix est élevé, moins il y a de ventes
        # Exemples:
        # - Produit à 5 DT: facteur ~2.0 (ventes fréquentes)
        # - Produit à 50 DT: facteur ~1.0 (ventes normales)
        # - Produit à 500 DT: facteur ~0.2 (ventes rares)
        # - Produit à 1250 DT: facteur ~0.08 (ventes très rares)
        if prix <= 10:
            price_factor = 2.0  # Produits très bon marché
        elif prix <= 50:
            price_factor = 1.5  # Produits bon marché
        elif prix <= 100:
            price_factor = 1.0  # Produits moyens
        elif prix <= 300:
            price_factor = 0.5  # Produits chers
        elif prix <= 600:
            price_factor = 0.2  # Produits très chers
        else:
            # Produits extrêmement chers (comme hospital bed à 1250 DT)
            # Facteur inversement proportionnel au prix
            price_factor = max(0.05, 50.0 / prix)  # Minimum 0.05 pour éviter 0
        
        return base_rate * price_factor

