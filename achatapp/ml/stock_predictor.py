"""
Module ML pour la prédiction de rupture de stock utilisant Random Forest
"""
import os
import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

# Chemin pour sauvegarder le modèle
MODEL_DIR = os.path.join(settings.BASE_DIR, 'achatapp', 'ml', 'models')
MODEL_PATH = os.path.join(MODEL_DIR, 'stock_predictor.joblib')

# Créer le dossier models s'il n'existe pas
os.makedirs(MODEL_DIR, exist_ok=True)


class StockPredictor:
    """Classe pour prédire les jours jusqu'à rupture de stock avec Random Forest"""
    
    def __init__(self):
        self.model = None
        self.label_encoders = {}
        self.is_trained = False
        self.load_model()
    
    def load_model(self):
        """Charge le modèle depuis le disque s'il existe"""
        try:
            if os.path.exists(MODEL_PATH):
                model_data = joblib.load(MODEL_PATH)
                self.model = model_data.get('model')
                self.label_encoders = model_data.get('label_encoders', {})
                self.is_trained = True
                logger.info("Modèle ML chargé avec succès")
            else:
                logger.warning("Aucun modèle trouvé, initialisation d'un nouveau modèle")
        except Exception as e:
            logger.error(f"Erreur lors du chargement du modèle: {e}")
            self.is_trained = False
    
    def prepare_features(self, data_df):
        """Prépare les features pour l'entraînement ou la prédiction"""
        df = data_df.copy()
        
        # Encoder les catégories
        if 'category' in df.columns:
            if 'category' not in self.label_encoders:
                self.label_encoders['category'] = LabelEncoder()
                df['category_encoded'] = self.label_encoders['category'].fit_transform(df['category'])
            else:
                # Gérer les nouvelles catégories non vues pendant l'entraînement
                try:
                    df['category_encoded'] = self.label_encoders['category'].transform(df['category'])
                except ValueError:
                    # Si nouvelle catégorie, utiliser la valeur la plus fréquente
                    df['category_encoded'] = 0
        
        # Features numériques
        features = []
        
        # Quantité actuelle
        if 'current_stock' in df.columns:
            features.append(df['current_stock'].values)
        
        # Moyenne des ventes par jour
        if 'avg_daily_sales' in df.columns:
            features.append(df['avg_daily_sales'].values)
        
        # Catégorie encodée
        if 'category_encoded' in df.columns:
            features.append(df['category_encoded'].values)
        
        # Prix de vente (normalisé)
        if 'prix_vente' in df.columns:
            features.append(df['prix_vente'].values)
        
        # Tendance des ventes (7 derniers jours)
        if 'trend_7days' in df.columns:
            features.append(df['trend_7days'].values)
        else:
            features.append(np.zeros(len(df)))
        
        # Variance des ventes
        if 'sales_variance' in df.columns:
            features.append(df['sales_variance'].values)
        else:
            features.append(np.zeros(len(df)))
        
        # Assembler les features
        if features:
            X = np.column_stack(features)
        else:
            X = np.array([]).reshape(len(df), 0)
        
        return X
    
    def train(self, historical_data):
        """
        Entraîne le modèle Random Forest sur les données historiques
        
        Args:
            historical_data: DataFrame avec colonnes:
                - current_stock: stock actuel
                - avg_daily_sales: moyenne des ventes par jour
                - category: catégorie du produit
                - prix_vente: prix de vente
                - trend_7days: tendance des 7 derniers jours
                - sales_variance: variance des ventes
                - days_until_out_of_stock: cible (jours jusqu'à rupture)
        """
        try:
            if historical_data.empty or len(historical_data) < 10:
                logger.warning("Pas assez de données pour entraîner le modèle (minimum 10 échantillons)")
                return False
            
            # Préparer les features
            X = self.prepare_features(historical_data)
            
            # Cible: jours jusqu'à rupture de stock
            if 'days_until_out_of_stock' not in historical_data.columns:
                logger.error("Colonne 'days_until_out_of_stock' manquante dans les données")
                return False
            
            y = historical_data['days_until_out_of_stock'].values
            
            # Filtrer les valeurs invalides
            valid_mask = (y > 0) & (y <= 365) & np.isfinite(y) & np.isfinite(X).all(axis=1)
            X = X[valid_mask]
            y = y[valid_mask]
            
            if len(X) < 10:
                logger.warning("Pas assez de données valides après filtrage")
                return False
            
            # Diviser en train/test
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, random_state=42
            )
            
            # Créer et entraîner le modèle Random Forest
            self.model = RandomForestRegressor(
                n_estimators=100,
                max_depth=10,
                min_samples_split=5,
                min_samples_leaf=2,
                random_state=42,
                n_jobs=-1
            )
            
            self.model.fit(X_train, y_train)
            
            # Évaluer le modèle
            train_score = self.model.score(X_train, y_train)
            test_score = self.model.score(X_test, y_test)
            
            logger.info(f"Modèle entraîné - Train Score: {train_score:.4f}, Test Score: {test_score:.4f}")
            
            # Sauvegarder le modèle
            self.save_model()
            
            self.is_trained = True
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors de l'entraînement du modèle: {e}")
            return False
    
    def predict(self, product_features):
        """
        Prédit les jours jusqu'à rupture de stock pour un produit
        
        Args:
            product_features: dict avec les features du produit:
                - current_stock: stock actuel
                - avg_daily_sales: moyenne des ventes par jour
                - category: catégorie du produit
                - prix_vente: prix de vente
                - trend_7days: tendance des 7 derniers jours (optionnel)
                - sales_variance: variance des ventes (optionnel)
        
        Returns:
            int: Nombre de jours jusqu'à rupture de stock (ou None en cas d'erreur)
        """
        try:
            if not self.is_trained or self.model is None:
                logger.warning("Modèle non entraîné, utilisation de la méthode simple")
                return None
            
            # Créer un DataFrame pour le produit
            df = pd.DataFrame([product_features])
            
            # Préparer les features
            X = self.prepare_features(df)
            
            if X.shape[1] == 0:
                logger.warning("Aucune feature disponible pour la prédiction")
                return None
            
            # Faire la prédiction
            prediction = self.model.predict(X)
            
            # Arrondir et s'assurer que c'est un nombre positif
            days = max(0, int(round(prediction[0])))
            
            return days
            
        except Exception as e:
            logger.error(f"Erreur lors de la prédiction: {e}")
            return None
    
    def save_model(self):
        """Sauvegarde le modèle sur le disque"""
        try:
            model_data = {
                'model': self.model,
                'label_encoders': self.label_encoders
            }
            joblib.dump(model_data, MODEL_PATH)
            logger.info(f"Modèle sauvegardé dans {MODEL_PATH}")
        except Exception as e:
            logger.error(f"Erreur lors de la sauvegarde du modèle: {e}")


def get_simple_prediction(current_stock, avg_daily_sales, prix_vente=None):
    """
    Méthode simple de fallback pour calculer les jours jusqu'à rupture de stock
    Utilisée si le modèle ML n'est pas disponible ou échoue
    
    Args:
        current_stock: Stock actuel
        avg_daily_sales: Moyenne des ventes par jour
        prix_vente: Prix de vente du produit (optionnel, pour ajustement)
    
    Returns:
        int: Nombre de jours jusqu'à rupture de stock
    """
    if avg_daily_sales <= 0:
        return 999  # Pas de ventes = pas de rupture prévue
    
    # Ajuster les ventes quotidiennes selon le prix (produits chers = moins de ventes)
    if prix_vente:
        prix = float(prix_vente)
        if prix > 1000:
            # Produits très chers: ventes très rares (0.01-0.1 par jour)
            avg_daily_sales = min(avg_daily_sales, max(0.01, current_stock / 3650))  # Max 10 ans
        elif prix > 500:
            # Produits chers: ventes rares (0.1-0.3 par jour)
            avg_daily_sales = min(avg_daily_sales, max(0.1, current_stock / 1800))  # Max 5 ans
        elif prix > 200:
            # Produits moyens-chers: ventes modérées (0.3-0.8 par jour)
            avg_daily_sales = min(avg_daily_sales, max(0.3, current_stock / 900))  # Max ~2.5 ans
        # Produits bon marché: garder avg_daily_sales tel quel
    
    days = int(current_stock / avg_daily_sales) if avg_daily_sales > 0 else 999
    return max(0, days)


# Instance globale du prédicteur
_predictor_instance = None


def get_predictor():
    """Récupère l'instance globale du prédicteur (singleton)"""
    global _predictor_instance
    if _predictor_instance is None:
        _predictor_instance = StockPredictor()
    return _predictor_instance

