# Système ML de Prédiction de Rupture de Stock

Ce module implémente un système de prédiction de rupture de stock utilisant Random Forest pour prédire le nombre de jours jusqu'à rupture de stock.

## Structure

- `stock_predictor.py` : Module principal contenant la classe `StockPredictor` avec le modèle Random Forest
- `models/` : Dossier contenant les modèles entraînés sauvegardés (fichiers .joblib)

## Installation

Assurez-vous d'avoir installé les dépendances nécessaires :

```bash
pip install scikit-learn pandas numpy joblib
```

## Utilisation

### 1. Générer les données historiques

Génère des commandes historiques pour l'entraînement :

```bash
python manage.py generate_historical_orders --days 90
```

Options :
- `--days` : Nombre de jours de données à générer (défaut: 90)
- `--force` : Force la régénération même si des données existent déjà

### 2. Entraîner le modèle ML

Entraîne le modèle Random Forest sur les données historiques :

```bash
python manage.py train_stock_model --days 90
```

### 3. Utilisation dans le code

Le modèle est automatiquement utilisé dans les vues Django :

```python
from achatapp.models import Produit

product = Produit.objects.get(id=1)

# Obtenir les jours jusqu'à rupture de stock
days = product.get_days_until_out_of_stock()

# Obtenir le statut complet du stock
stock_status = product.get_stock_status()
# Retourne: {'status': 'low'|'medium'|'good'|'out', 'days_until_out': int, 'message': str, 'color': str}
```

## Workflow automatique

Lors de l'ajout d'un nouveau produit via `product_add`, le système :
1. Génère automatiquement des données historiques (90 jours)
2. Entraîne le modèle ML en arrière-plan
3. Les prédictions sont ensuite disponibles immédiatement

## Méthode de fallback

Si le modèle ML n'est pas disponible ou échoue, le système utilise une méthode simple basée sur :
- Stock actuel
- Moyenne des ventes par jour

Formule : `jours = stock_actuel / moyenne_ventes_journalières`

## Features du modèle ML

Le modèle Random Forest utilise les features suivantes :
- Stock actuel
- Moyenne des ventes par jour (90 derniers jours)
- Tendance des 7 derniers jours
- Variance des ventes
- Catégorie du produit (encodée)
- Prix de vente

## Statuts de stock

- **out** : Rupture de stock (quantité = 0)
- **low** : Stock faible (≤ 7 jours)
- **medium** : Stock moyen (8-30 jours)
- **good** : Stock suffisant (> 30 jours)


