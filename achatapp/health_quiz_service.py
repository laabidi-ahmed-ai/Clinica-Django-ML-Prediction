"""
Service de gestion du quiz santé avec API externe et fallback local
Montre: Séparation des responsabilités, Design Pattern Service, Gestion d'erreurs
"""

try:
    import requests
except ImportError:
    requests = None
import random
import html
from django.core.cache import cache
from django.conf import settings


class HealthQuizService:
    """Service pour gérer les questions de santé depuis API avec fallback local"""
    
    API_URL = "https://opentdb.com/api.php"
    CACHE_TIMEOUT = 3600  # 1 heure
    
    # Fallback: High-quality local questions (no admin needed)
    FALLBACK_QUESTIONS = [
        {
            'question': 'What is the recommended daily water intake for an adult?',
            'options': ['1 liter', '2-3 liters', '5 liters', '500ml'],
            'correct_index': 1,
            'explanation': 'WHO recommends 2-3 liters of water per day for an adult.'
        },
        {
            'question': 'How many hours of sleep are recommended for an adult?',
            'options': ['4-5 hours', '7-9 hours', '10-12 hours', '6 hours'],
            'correct_index': 1,
            'explanation': 'The National Sleep Foundation recommends 7-9 hours for adults.'
        },
        {
            'question': 'Which vitamin is mainly obtained through sun exposure?',
            'options': ['Vitamin A', 'Vitamin D', 'Vitamin C', 'Vitamin B12'],
            'correct_index': 1,
            'explanation': 'Vitamin D is synthesized by the skin under the effect of UV rays.'
        },
        {
            'question': 'How many steps per day are recommended to stay active?',
            'options': ['5000 steps', '10000 steps', '15000 steps', '20000 steps'],
            'correct_index': 1,
            'explanation': 'WHO recommends 10000 steps per day to maintain good health.'
        },
        {
            'question': 'What is the maximum recommended percentage of saturated fats in the diet?',
            'options': ['Less than 10%', '20-30%', '40-50%', 'More than 50%'],
            'correct_index': 0,
            'explanation': 'WHO recommends less than 10% of saturated fats in total energy intake.'
        },
        {
            'question': 'How many servings of fruits and vegetables are recommended per day?',
            'options': ['2 servings', '5 servings', '8 servings', '10 servings'],
            'correct_index': 1,
            'explanation': 'WHO recommends at least 5 servings of fruits and vegetables per day.'
        },
        {
            'question': 'What is the recommended maximum heart rate during exercise?',
            'options': ['120-140 bpm', '150-170 bpm', '180-200 bpm', '220 - age'],
            'correct_index': 3,
            'explanation': 'Maximum heart rate is calculated by: 220 - age (in years).'
        },
        {
            'question': 'How much moderate exercise is recommended per week?',
            'options': ['30 minutes', '150 minutes', '300 minutes', '450 minutes'],
            'correct_index': 1,
            'explanation': 'WHO recommends at least 150 minutes of moderate exercise per week.'
        },
        {
            'question': 'What is the normal body temperature for an adult?',
            'options': ['35°C', '36.5-37.5°C', '38°C', '39°C'],
            'correct_index': 1,
            'explanation': 'Normal body temperature ranges between 36.5°C and 37.5°C.'
        },
        {
            'question': 'How long does it take for water to be digested after consumption?',
            'options': ['5 minutes', '10-15 minutes', '30 minutes', '1 hour'],
            'correct_index': 1,
            'explanation': 'Water is generally absorbed within 10-15 minutes after consumption.'
        },
    ]
    
    @classmethod
    def get_questions(cls, count=3):
        """
        Récupère des questions depuis l'API avec fallback local
        Montre: Gestion d'erreurs, Caching, Fallback pattern
        """
        # Essayer l'API d'abord
        api_questions = cls._fetch_from_api()
        
        if api_questions and len(api_questions) >= count:
            selected = random.sample(api_questions, count)
            # Marquer la source
            for q in selected:
                q['source'] = 'API'
            return selected
        
        # Fallback: Questions locales
        return cls._get_fallback_questions(count)
    
    @classmethod
    def _fetch_from_api(cls):
        """Récupère questions depuis Open Trivia DB API"""
        if not requests:
            return None
        try:
            # Vérifier le cache d'abord
            cache_key = 'health_questions_api'
            cached = cache.get(cache_key)
            if cached:
                return cached
            
            params = {
                'amount': 10,
                'category': 17,  # Science & Nature (includes health questions)
                'difficulty': 'easy',
                'type': 'multiple',
                'encode': 'default'  # Ensure English encoding
            }
            
            response = requests.get(cls.API_URL, params=params, timeout=5)
            response.raise_for_status()
            
            data = response.json()
            
            if data.get('response_code') == 0:
                questions = []
                health_keywords = [
                    'health', 'body', 'vitamin', 'exercise', 'sleep', 
                    'water', 'diet', 'nutrition', 'food', 'muscle', 
                    'heart', 'blood', 'brain', 'immune', 'calorie',
                    'protein', 'carbohydrate', 'fat', 'mineral'
                ]
                
                for item in data['results']:
                    question_lower = item['question'].lower()
                    if any(kw in question_lower for kw in health_keywords):
                        options = item['incorrect_answers'] + [item['correct_answer']]
                        random.shuffle(options)
                        correct_index = options.index(item['correct_answer'])
                        
                        questions.append({
                            'question': cls._clean_html(item['question']),
                            'options': [cls._clean_html(opt) for opt in options],
                            'correct_index': correct_index,
                            'source': 'API'
                        })
                
                # Mettre en cache si on a des questions
                if questions:
                    cache.set(cache_key, questions, cls.CACHE_TIMEOUT)
                    return questions
                
        except (requests.RequestException, KeyError, ValueError) as e:
            # En production, utiliser logging au lieu de print
            print(f"API Error: {e}")
        
        return None
    
    @classmethod
    def _get_fallback_questions(cls, count):
        """Retourne questions locales en fallback"""
        selected = random.sample(cls.FALLBACK_QUESTIONS, 
                                min(count, len(cls.FALLBACK_QUESTIONS)))
        # Marquer la source
        for q in selected:
            q['source'] = 'Local'
        return selected
    
    @staticmethod
    def _clean_html(text):
        """Nettoie le HTML des questions de l'API"""
        return html.unescape(text)

