from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.core.exceptions import ValidationError
from django.conf import settings
from django.urls import reverse
from django.core.mail import send_mail, EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from decimal import Decimal
import json
import re
try:
    import stripe
except ImportError:
    stripe = None
import base64
import hashlib
import socket
import subprocess
import platform
from collections import defaultdict
from .models import Produit, Commande, Coupon
from .health_quiz_service import HealthQuizService
from io import BytesIO
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from datetime import datetime, timedelta
from django.utils import timezone
from django.core.management import call_command
import threading

# Configure Stripe (si disponible)
if stripe:
    stripe.api_key = settings.STRIPE_SECRET_KEY


def index(request):
    """Vue pour la page d'accueil"""
    produits = Produit.objects.all()
    
    # Recherche par nom
    search_query = request.GET.get('search', '').strip()
    if search_query:
        produits = produits.filter(nom__icontains=search_query)
    
    # Filtre par catégorie
    category_filter = request.GET.get('category', '')
    if category_filter:
        produits = produits.filter(category=category_filter)
    
    # Tri par prix
    sort_by = request.GET.get('sort', '')
    if sort_by == 'price_asc':
        produits = produits.order_by('prix_vente')
    elif sort_by == 'price_desc':
        produits = produits.order_by('-prix_vente')
    else:
        produits = produits.order_by('-date_ajout')
    
    # Compter les articles dans le panier
    panier = request.session.get('panier', {})
    nombre_articles = sum(item['quantite'] for item in panier.values())
    
    # Récupérer toutes les catégories pour le filtre
    categories = Produit.CATEGORY_CHOICES
    
    return render(request, 'front/products/index.html', {
        'produits': produits,
        'nombre_articles_panier': nombre_articles,
        'search_query': search_query,
        'category_filter': category_filter,
        'sort_by': sort_by,
        'categories': categories,
    })


def product_search_suggestions(request):
    """API endpoint for product search autocomplete"""
    query = request.GET.get('q', '').strip()
    
    if len(query) < 1:
        return JsonResponse({'suggestions': []})
    
    # Search products by name (case-insensitive)
    products = Produit.objects.filter(nom__icontains=query)[:10]
    
    suggestions = []
    for product in products:
        suggestions.append({
            'id': product.id,
            'name': product.nom,
            'category': product.get_category_display(),
            'price': float(product.prix_vente),
            'stock': product.quantite,
            'image': product.image.url if product.image else None,
        })
    
    return JsonResponse({'suggestions': suggestions})


def ajouter_au_panier(request, produit_id):
    """Vue pour ajouter un produit au panier"""
    if request.method == 'POST':
        produit = get_object_or_404(Produit, id=produit_id)
        quantite = int(request.POST.get('quantite', 1))
        
        # Initialiser le panier dans la session
        if 'panier' not in request.session:
            request.session['panier'] = {}
        
        panier = request.session['panier']
        produit_id_str = str(produit_id)
        
        # Vérifier le stock total (quantité déjà dans le panier + nouvelle quantité)
        quantite_existante = panier.get(produit_id_str, {}).get('quantite', 0)
        quantite_totale = quantite_existante + quantite
        
        if produit.quantite < quantite_totale:
            messages.error(request, f'Insufficient stock. Available stock: {produit.quantite}, already in cart: {quantite_existante}')
            return redirect('index')
        
        # Ajouter ou mettre à jour le produit dans le panier
        if produit_id_str in panier:
            panier[produit_id_str]['quantite'] += quantite
        else:
            panier[produit_id_str] = {
                'produit_id': produit_id,
                'nom': produit.nom,
                'prix_vente': str(produit.prix_vente),
                'quantite': quantite,
                'image': produit.image.url if produit.image else None,
            }
        
        request.session['panier'] = panier
        request.session.modified = True
        messages.success(request, f'{produit.nom} added to cart!')
        return redirect('panier')
    
    return redirect('index')


def modifier_quantite_panier(request, produit_id):
    """Vue pour modifier la quantité d'un produit dans le panier"""
    if request.method == 'POST':
        panier = request.session.get('panier', {})
        produit_id_str = str(produit_id)
        nouvelle_quantite = int(request.POST.get('quantite', 1))
        
        if produit_id_str in panier:
            try:
                produit = Produit.objects.get(id=produit_id)
                
                # Vérifier le stock
                if nouvelle_quantite <= 0:
                    # Si quantité <= 0, retirer le produit
                    del panier[produit_id_str]
                    messages.success(request, 'Product removed from cart')
                elif nouvelle_quantite > produit.quantite:
                    messages.error(request, f'Insufficient stock. Available stock: {produit.quantite}')
                else:
                    panier[produit_id_str]['quantite'] = nouvelle_quantite
                    messages.success(request, 'Quantity updated')
                
                request.session['panier'] = panier
                request.session.modified = True
            except Produit.DoesNotExist:
                messages.error(request, 'Product not found')
    
    return redirect('panier')


def retirer_du_panier(request, produit_id):
    """Vue pour retirer un produit du panier"""
    panier = request.session.get('panier', {})
    produit_id_str = str(produit_id)
    
    if produit_id_str in panier:
        del panier[produit_id_str]
        request.session['panier'] = panier
        request.session.modified = True
        messages.success(request, 'Product removed from cart')
    
    return redirect('panier')


def vider_panier(request):
    """Vue pour vider complètement le panier"""
    if 'panier' in request.session:
        del request.session['panier']
        request.session.modified = True
        messages.success(request, 'Cart emptied')
    
    return redirect('panier')


def panier(request):
    """Vue pour afficher le panier avec gestion des coupons"""
    panier = request.session.get('panier', {})
    articles = []
    total = Decimal('0.00')
    produits_a_supprimer = []
    
    for produit_id_str, item in panier.items():
        try:
            produit = Produit.objects.get(id=item['produit_id'])
            quantite = item['quantite']
            prix = Decimal(item['prix_vente'])
            sous_total = prix * quantite
            total += sous_total
            
            articles.append({
                'produit': produit,
                'quantite': quantite,
                'prix': prix,
                'sous_total': sous_total,
                'image': item.get('image'),
            })
        except Produit.DoesNotExist:
            # Produit supprimé, on le retire du panier après l'itération
            produits_a_supprimer.append(produit_id_str)
    
    # Supprimer les produits introuvables du panier
    for produit_id_str in produits_a_supprimer:
        del panier[produit_id_str]
    
    if produits_a_supprimer:
        request.session['panier'] = panier
        request.session.modified = True
    
    # Gestion des coupons
    coupon_code = None
    discount = Decimal('0.00')
    coupon_error = None
    
    # NE PAS appliquer automatiquement le coupon depuis la session
    # L'utilisateur doit cliquer sur "Appliquer" pour l'utiliser
    # Le code sera pré-rempli dans le champ mais pas appliqué automatiquement
    
    # Appliquer un coupon manuellement
    if request.method == 'POST' and 'apply_coupon' in request.POST:
        coupon_code_input = request.POST.get('coupon_code', '').strip().upper()
        if coupon_code_input:
            try:
                coupon = Coupon.objects.get(code=coupon_code_input)
                is_valid, error_msg = coupon.is_valid(request.user if request.user.is_authenticated else None)
                if is_valid:
                    coupon_code = coupon_code_input
                    discount = (total * Decimal(str(coupon.discount_percent))) / Decimal('100')
                    request.session['coupon_code'] = coupon_code
                    messages.success(request, f'Coupon appliqué! Réduction de {coupon.discount_percent}%')
                else:
                    coupon_error = error_msg
                    messages.error(request, error_msg)
            except Coupon.DoesNotExist:
                coupon_error = "Code coupon invalide"
                messages.error(request, "Code coupon invalide")
    
    total_after_discount = total - discount
    
    # Vérifier les résultats du quiz depuis la session
    quiz_result = request.session.get('quiz_result')
    quiz_score = request.session.get('quiz_score')
    quiz_coupon_code = request.session.get('quiz_coupon_code')
    
    # Nettoyer la session après avoir récupéré les données
    if quiz_result:
        request.session.pop('quiz_result', None)
        request.session.pop('quiz_score', None)
        if quiz_coupon_code:
            request.session.pop('quiz_coupon_code', None)
    
    # Pré-remplir le champ coupon avec le code de la session (si présent)
    # Mais ne pas l'appliquer automatiquement
    session_coupon_code = request.session.get('coupon_code', '')
    
    nombre_articles = sum(item['quantite'] for item in panier.values())
    return render(request, 'front/products/panier.html', {
        'articles': articles,
        'coupon_code': coupon_code,  # Seulement si appliqué via le bouton
        'discount': discount,
        'total_after_discount': total_after_discount,
        'coupon_error': coupon_error,
        'total': total,
        'nombre_articles': nombre_articles,
        'nombre_articles_panier': nombre_articles,
        'quiz_result': quiz_result,
        'quiz_score': quiz_score,
        'quiz_coupon_code': quiz_coupon_code,
        'session_coupon_code': session_coupon_code,  # Pour pré-remplir le champ
    })


def passer_commande(request):
    """Vue pour passer la commande depuis le panier - redirige vers Stripe"""
    if request.method == 'POST':
        panier = request.session.get('panier', {})
        
        if not panier:
            messages.error(request, 'Your cart is empty')
            return redirect('panier')
        
        # Récupérer les informations du formulaire
        nom_client = request.POST.get('nom_client', '').strip()
        prenom_client = request.POST.get('prenom_client', '').strip()
        email_client = request.POST.get('email_client', '').strip()
        telephone_client = request.POST.get('telephone_client', '').strip()
        adresse_client = request.POST.get('adresse_client', '').strip()
        
        # Validation de base - champs vides
        if not all([nom_client, prenom_client, email_client, telephone_client, adresse_client]):
            messages.error(request, 'Please fill in all form fields')
            return redirect('panier')
        
        # Validation Last Name - pas de nombres ni caractères spéciaux
        name_pattern = re.compile(r'^[a-zA-ZÀ-ÿ\s\'-]+$')
        if not name_pattern.match(nom_client):
            messages.error(request, 'Last name cannot contain numbers or special characters')
            return redirect('panier')
        
        # Validation First Name - pas de nombres ni caractères spéciaux
        if not name_pattern.match(prenom_client):
            messages.error(request, 'First name cannot contain numbers or special characters')
            return redirect('panier')
        
        # Validation Email - format email valide
        email_pattern = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
        if not email_pattern.match(email_client):
            messages.error(request, 'Please enter a valid email address')
            return redirect('panier')
        
        # Validation Phone - uniquement des nombres, exactement 8 chiffres
        phone_pattern = re.compile(r'^[0-9]{8}$')
        if not phone_pattern.match(telephone_client):
            messages.error(request, 'Phone number must contain exactly 8 digits')
            return redirect('panier')
        
        # Validation Address - minimum 5 caractères
        if len(adresse_client) < 5:
            messages.error(request, 'Address must contain at least 5 characters')
            return redirect('panier')
        
        # Verify stock before proceeding to payment
        for produit_id_str, item in panier.items():
            try:
                produit = Produit.objects.get(id=item['produit_id'])
                if produit.quantite < item['quantite']:
                    messages.error(request, f'Insufficient stock for {produit.nom}. Available stock: {produit.quantite}')
                    return redirect('panier')
            except Produit.DoesNotExist:
                messages.error(request, f'Product no longer exists')
                return redirect('panier')
        
        # Store order info in session for after payment
        request.session['pending_order'] = {
            'nom_client': nom_client,
            'prenom_client': prenom_client,
            'email_client': email_client,
            'telephone_client': telephone_client,
            'adresse_client': adresse_client,
        }
        request.session.modified = True
        
        # Calculate total for Stripe
        total = Decimal('0.00')
        line_items = []
        
        # Calculer le total initial
        for produit_id_str, item in panier.items():
            produit = Produit.objects.get(id=item['produit_id'])
            item_total = produit.prix_vente * item['quantite']
            total += item_total
        
        # Appliquer le coupon si présent
        discount = Decimal('0.00')
        coupon_code = request.session.get('coupon_code', None)
        total_after_discount = total
        if coupon_code:
            try:
                coupon = Coupon.objects.get(code=coupon_code)
                is_valid, error_msg = coupon.is_valid(request.user if request.user.is_authenticated else None)
                if is_valid:
                    discount = (total * Decimal(str(coupon.discount_percent))) / Decimal('100')
                    total_after_discount = total - discount
                    # Marquer le coupon comme utilisé après le paiement réussi
                    request.session['coupon_to_apply'] = coupon_code
            except Coupon.DoesNotExist:
                pass
        
        # Créer les line_items avec les prix ajustés pour refléter la réduction
        if discount > 0:
            # Si un coupon est appliqué, ajuster proportionnellement les prix
            discount_ratio = total_after_discount / total if total > 0 else Decimal('1.00')
            for produit_id_str, item in panier.items():
                produit = Produit.objects.get(id=item['produit_id'])
                # Ajuster le prix unitaire proportionnellement
                adjusted_price = produit.prix_vente * discount_ratio
                line_items.append({
                    'price_data': {
                        'currency': 'usd',
                        'product_data': {
                            'name': produit.nom,
                            'description': produit.description[:500] if produit.description else 'Medical product',
                        },
                        'unit_amount': int(adjusted_price * 100),  # Stripe uses cents
                    },
                    'quantity': item['quantite'],
                })
        else:
            # Pas de coupon, utiliser les prix originaux
            for produit_id_str, item in panier.items():
                produit = Produit.objects.get(id=item['produit_id'])
                line_items.append({
                    'price_data': {
                        'currency': 'usd',
                        'product_data': {
                            'name': produit.nom,
                            'description': produit.description[:500] if produit.description else 'Medical product',
                        },
                        'unit_amount': int(produit.prix_vente * 100),  # Stripe uses cents
                    },
                    'quantity': item['quantite'],
                })
        
        try:
            # Create Stripe Checkout Session
            checkout_session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=line_items,
                mode='payment',
                customer_email=email_client,
                success_url=request.build_absolute_uri(reverse('payment_success')) + '?session_id={CHECKOUT_SESSION_ID}',
                cancel_url=request.build_absolute_uri(reverse('payment_cancel')),
                metadata={
                    'nom_client': nom_client,
                    'prenom_client': prenom_client,
                    'email_client': email_client,
                    'telephone_client': telephone_client,
                },
            )
            
            return redirect(checkout_session.url)
            
        except stripe.error.StripeError as e:
            messages.error(request, f'Payment error: {str(e)}')
            return redirect('panier')
    
    return redirect('panier')


def payment_success(request):
    """Handle successful payment from Stripe"""
    session_id = request.GET.get('session_id')
    
    if not session_id:
        messages.error(request, 'Invalid payment session')
        return redirect('index')
    
    try:
        # Verify the session with Stripe
        session = stripe.checkout.Session.retrieve(session_id)
        
        if session.payment_status == 'paid':
            panier = request.session.get('panier', {})
            pending_order = request.session.get('pending_order', {})
            
            if not panier or not pending_order:
                messages.error(request, 'Session expired. Please try again.')
                return redirect('panier')
            
            # Récupérer le montant réellement payé depuis Stripe (en cents, donc diviser par 100)
            amount_paid = Decimal(str(session.amount_total)) / Decimal('100')  # Stripe retourne en cents
            
            # Calculer le total initial pour répartir proportionnellement
            total_initial = Decimal('0.00')
            items_data = []
            for produit_id_str, item in panier.items():
                try:
                    produit = Produit.objects.get(id=item['produit_id'])
                    item_total = produit.prix_vente * item['quantite']
                    total_initial += item_total
                    items_data.append({
                        'produit': produit,
                        'quantite': item['quantite'],
                        'item_total': item_total
                    })
                except Produit.DoesNotExist:
                    continue
            
            commandes_crees = []
            
            # Create orders for each product in the cart avec montant réellement payé
            for item_data in items_data:
                try:
                    # Calculer la proportion de ce produit dans le total
                    if total_initial > 0:
                        proportion = item_data['item_total'] / total_initial
                        # Répartir le montant payé proportionnellement
                        item_amount_paid = amount_paid * proportion
                    else:
                        item_amount_paid = item_data['item_total']
                    
                    # Create the order avec le montant réellement payé
                    commande = Commande.objects.create(
                        produit=item_data['produit'],
                        quantite=item_data['quantite'],
                        nom_client=pending_order['nom_client'],
                        prenom_client=pending_order['prenom_client'],
                        email_client=pending_order['email_client'],
                        telephone_client=pending_order['telephone_client'],
                        adresse_client=pending_order['adresse_client'],
                        amount_paid=item_amount_paid,  # Stocker le montant réellement payé
                    )
                    commandes_crees.append(commande)
                    
                except Exception as e:
                    continue
            
            # Appliquer le coupon après paiement réussi
            coupon_code = request.session.get('coupon_to_apply')
            if coupon_code:
                try:
                    coupon = Coupon.objects.get(code=coupon_code)
                    coupon.apply_to_user(request.user if request.user.is_authenticated else None)
                    request.session.pop('coupon_to_apply', None)
                    request.session.pop('coupon_code', None)
                except Coupon.DoesNotExist:
                    pass
            
            # Clear the cart and pending order
            if 'panier' in request.session:
                del request.session['panier']
            if 'pending_order' in request.session:
                del request.session['pending_order']
            request.session.modified = True
            
            if commandes_crees:
                messages.success(request, f'Payment successful! {len(commandes_crees)} order(s) created. Your orders are pending validation.')
            
            return render(request, 'front/products/payment_success.html', {
                'commandes': commandes_crees,
                'total': amount_paid,  # Utiliser le montant réellement payé depuis Stripe
            })
        else:
            messages.error(request, 'Payment was not completed')
            return redirect('panier')
            
    except stripe.error.StripeError as e:
        messages.error(request, f'Error verifying payment: {str(e)}')
        return redirect('panier')


def payment_cancel(request):
    """Handle cancelled payment from Stripe"""
    messages.warning(request, 'Payment was cancelled. Your cart is still available.')
    return redirect('panier')


def acheter_produit(request, produit_id):
    """Vue pour créer une commande pour un produit (ancienne méthode, redirige vers panier)"""
    return redirect('ajouter_au_panier', produit_id=produit_id)


def service_details(request):
    """Vue pour les détails d'un service"""
    return render(request, 'service-details.html')


def starter_page(request):
    """Vue pour la page de démarrage"""
    return render(request, 'starter-page.html')


def dashboard(request):
    """Vue pour le tableau de bord admin"""
    from datetime import date, timedelta
    from django.db.models import Sum, Count
    
    total_orders = Commande.objects.count()
    pending_orders = Commande.objects.filter(statut='en_attente').count()
    accepted_orders = Commande.objects.filter(statut='acceptee').count()
    total_products = Produit.objects.count()
    total_revenue = sum(order.total for order in Commande.objects.filter(statut='acceptee'))
    
    # Orders today
    today = date.today()
    orders_today = Commande.objects.filter(
        date_creation__date=today,
        statut='acceptee'
    ).count()
    
    # Recent orders (last 10)
    recent_orders = Commande.objects.all().order_by('-date_creation')[:10]
    
    # Latest pending order
    latest_pending = Commande.objects.filter(statut='en_attente').order_by('-date_creation').first()
    
    # Recent products (last 5)
    recent_products = Produit.objects.all().order_by('-date_ajout')[:5]
    
    # Calculate acceptance rate
    if total_orders > 0:
        acceptance_rate = round((accepted_orders / total_orders) * 100, 1)
    else:
        acceptance_rate = 0
    
    # Statistics: Most bought products (from accepted orders)
    accepted_orders_list = Commande.objects.filter(statut='acceptee').select_related('produit')
    product_stats = defaultdict(lambda: {'quantity': 0, 'name': ''})
    
    for order in accepted_orders_list:
        product_id = order.produit.id
        product_stats[product_id]['quantity'] += order.quantite
        product_stats[product_id]['name'] = order.produit.nom
    
    # Sort by quantity and get top products
    sorted_products = sorted(product_stats.items(), key=lambda x: x[1]['quantity'], reverse=True)
    total_quantity_sold = sum(stats['quantity'] for _, stats in sorted_products)
    
    # Prepare data for pie chart and template
    product_stats_list = []
    product_labels = []
    product_quantities = []
    
    for product_id, stats in sorted_products[:10]:  # Top 10 products
        if total_quantity_sold > 0:
            percentage = round((stats['quantity'] / total_quantity_sold) * 100, 1)
        else:
            percentage = 0
        product_stats_list.append({
            'name': stats['name'],
            'quantity': stats['quantity'],
            'percentage': percentage
        })
        product_labels.append(stats['name'])
        product_quantities.append(stats['quantity'])
    
    # Calculate profit statistics (Selling Price - Purchase Price)
    total_profit = Decimal('0.00')
    product_profits = []
    
    for order in accepted_orders_list:
        profit_per_unit = order.produit.prix_vente - order.produit.prix_achat
        profit_for_order = profit_per_unit * order.quantite
        total_profit += profit_for_order
    
    # Profit by product
    profit_by_product = defaultdict(lambda: {'profit': Decimal('0.00'), 'name': '', 'quantity': 0})
    
    for order in accepted_orders_list:
        product_id = order.produit.id
        profit_per_unit = order.produit.prix_vente - order.produit.prix_achat
        profit_for_order = profit_per_unit * order.quantite
        profit_by_product[product_id]['profit'] += profit_for_order
        profit_by_product[product_id]['name'] = order.produit.nom
        profit_by_product[product_id]['quantity'] += order.quantite
    
    # Sort by profit
    sorted_profit = sorted(profit_by_product.items(), key=lambda x: x[1]['profit'], reverse=True)
    
    # Prepare profit data for template
    profit_stats_list = []
    for product_id, stats in sorted_profit[:10]:
        profit_stats_list.append({
            'name': stats['name'],
            'quantity': stats['quantity'],
            'profit': float(stats['profit'])
        })
    # Revenue by period (Last 7 days, 30 days, 12 months)
    revenue_by_day = []
    revenue_by_month = []
    
    # Last 7 days revenue
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        day_orders = Commande.objects.filter(
            date_creation__date=day,
            statut='acceptee'
        )
        day_revenue = sum(order.total for order in day_orders)
        revenue_by_day.append({
            'date': day.strftime('%Y-%m-%d'),
            'label': day.strftime('%b %d'),
            'revenue': float(day_revenue)
        })
    
    # Last 12 months revenue
    from calendar import monthrange
    for i in range(11, -1, -1):
        # Calculate month date
        target_month = today.month - i
        target_year = today.year
        while target_month <= 0:
            target_month += 12
            target_year -= 1
        
        month_start = date(target_year, target_month, 1)
        days_in_month = monthrange(target_year, target_month)[1]
        month_end = date(target_year, target_month, days_in_month) + timedelta(days=1)
        
        month_orders = Commande.objects.filter(
            date_creation__gte=month_start,
            date_creation__lt=month_end,
            statut='acceptee'
        )
        month_revenue = sum(order.total for order in month_orders)
        revenue_by_month.append({
            'date': month_start.strftime('%Y-%m'),
            'label': month_start.strftime('%b %Y'),
            'revenue': float(month_revenue)
        })
    
    # Top selling products (by revenue)
    top_products_by_revenue = []
    revenue_by_product = defaultdict(lambda: {'revenue': Decimal('0.00'), 'name': '', 'quantity': 0})
    
    for order in accepted_orders_list:
        product_id = order.produit.id
        revenue_by_product[product_id]['revenue'] += order.total
        revenue_by_product[product_id]['name'] = order.produit.nom
        revenue_by_product[product_id]['quantity'] += order.quantite
    
    sorted_revenue = sorted(revenue_by_product.items(), key=lambda x: x[1]['revenue'], reverse=True)
    
    for product_id, stats in sorted_revenue[:10]:
        top_products_by_revenue.append({
            'name': stats['name'],
            'revenue': float(stats['revenue']),
            'quantity': stats['quantity']
        })
    
    # Cart to Order Conversion Rate
    # Calculate based on orders with payment (Stripe) vs total orders
    # Orders that reached payment = better conversion indicator
    orders_with_payment = Commande.objects.filter(
        statut='acceptee',
        date_creation__gte=today - timedelta(days=30)
    ).count()
    
    # Estimate cart sessions: orders * 2.5 (industry average)
    estimated_cart_sessions = orders_with_payment * 2.5 if orders_with_payment > 0 else 1
    conversion_rate = round((orders_with_payment / estimated_cart_sessions) * 100, 2) if estimated_cart_sessions > 0 else 0
    
    # Orders per day average
    orders_per_day_avg = 0
    if total_orders > 0:
        first_order = Commande.objects.order_by('date_creation').first()
        if first_order:
            days_since_first = (today - first_order.date_creation.date()).days
            if days_since_first > 0:
                orders_per_day_avg = round(total_orders / days_since_first, 2)
    
    # Low stock alert - products with quantity < 10
    LOW_STOCK_THRESHOLD = 10
    low_stock_products = Produit.objects.filter(quantite__lt=LOW_STOCK_THRESHOLD).order_by('quantite')
    return render(request, 'back/products/dashboardProduct.html', {
        'total_orders': total_orders,
        'pending_orders': pending_orders,
        'accepted_orders': accepted_orders,
        'orders_today': orders_today,
        'total_products': total_products,
        'total_revenue': total_revenue,
        'recent_orders': recent_orders,
        'latest_pending': latest_pending,
        'recent_products': recent_products,
        'acceptance_rate': acceptance_rate,
        'product_stats_list': product_stats_list,
        'product_labels_json': json.dumps(product_labels),
        'product_quantities_json': json.dumps(product_quantities),
        'total_quantity_sold': total_quantity_sold,
        'total_profit': total_profit,
        'profit_stats_list': profit_stats_list,
        'low_stock_products': low_stock_products,
        'low_stock_threshold': LOW_STOCK_THRESHOLD,
        # New analytics data
        'revenue_by_day': revenue_by_day,
        'revenue_by_month': revenue_by_month,
        'revenue_by_day_json': json.dumps([{'date': r['label'], 'revenue': r['revenue']} for r in revenue_by_day]),
        'revenue_by_month_json': json.dumps([{'date': r['label'], 'revenue': r['revenue']} for r in revenue_by_month]),
        'top_products_by_revenue': top_products_by_revenue,
        'top_products_revenue_json': json.dumps([{'name': p['name'], 'revenue': p['revenue']} for p in top_products_by_revenue[:5]]),
        'conversion_rate': conversion_rate,
        'orders_per_day_avg': orders_per_day_avg,
    })


def orders_list(request):
    """Vue pour lister les commandes"""
    orders = Commande.objects.all().order_by('-date_creation')
    
    # Filter by status if provided
    status_filter = request.GET.get('status')
    if status_filter:
        orders = orders.filter(statut=status_filter)
    
    return render(request, 'back/products/orders.html', {'orders': orders})


def confirm_order(request, order_id):
    """Vue pour confirmer une commande et envoyer un email de confirmation"""
    order = get_object_or_404(Commande, id=order_id)
    
    if request.method == 'POST':
        try:
            order.accepter()
            
            # Send confirmation email
            if order.email_client:
                try:
                    import sys
                    print(f"[DEBUG] Sending email for order #{order.id} to {order.email_client}", file=sys.stderr)
                    sys.stderr.flush()
                    send_order_confirmation_email(order, request)
                    messages.success(request, f'Order #{order.id} confirmed successfully! Confirmation email sent to {order.email_client}')
                except Exception as e:
                    import sys
                    print(f"[ERROR] Failed to send email: {str(e)}", file=sys.stderr)
                    sys.stderr.flush()
                    messages.warning(request, f'Order #{order.id} confirmed but email could not be sent: {str(e)}')
            else:
                messages.success(request, f'Order #{order.id} confirmed successfully! (No email address provided)')
                
        except ValidationError as e:
            messages.error(request, str(e))
    
    return redirect('orders_list')


def generate_order_token(order):
    """Generate a unique token for order tracking"""
    data = f"{order.id}-{order.email_client}-{order.date_creation}"
    return hashlib.sha256(data.encode()).hexdigest()[:20]


def get_local_ip():
    """Get the local network IP address (not 127.0.0.1)"""
    # Try multiple methods to get the local IP
    ip_addresses = []
    
    # Method 1: Connect to external address
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0)
        try:
            s.connect(('8.8.8.8', 80))
            ip = s.getsockname()[0]
            if ip and ip != '127.0.0.1':
                ip_addresses.append(ip)
        except Exception:
            pass
        finally:
            s.close()
    except Exception:
        pass
    
    # Method 2: Get hostname and resolve
    try:
        hostname = socket.gethostname()
        ip = socket.gethostbyname(hostname)
        if ip and ip != '127.0.0.1' and ip not in ip_addresses:
            ip_addresses.append(ip)
    except Exception:
        pass
    
    # Method 3: Get all network interfaces
    try:
        system = platform.system()
        
        if system == "Windows":
            # Windows: ipconfig
            result = subprocess.run(['ipconfig'], capture_output=True, text=True, timeout=2)
            for line in result.stdout.split('\n'):
                if 'IPv4' in line or 'IP Address' in line:
                    parts = line.split(':')
                    if len(parts) > 1:
                        ip = parts[1].strip()
                        if ip and ip != '127.0.0.1' and '.' in ip and ip not in ip_addresses:
                            # Check if it's a valid IP
                            try:
                                socket.inet_aton(ip)
                                ip_addresses.append(ip)
                            except:
                                pass
        else:
            # Linux/Mac: ifconfig or ip
            try:
                result = subprocess.run(['hostname', '-I'], capture_output=True, text=True, timeout=2)
                ips = result.stdout.strip().split()
                for ip in ips:
                    if ip and ip != '127.0.0.1' and '.' in ip and ip not in ip_addresses:
                        try:
                            socket.inet_aton(ip)
                            ip_addresses.append(ip)
                        except:
                            pass
            except:
                pass
    except Exception:
        pass
    
    # Return first valid IP found, or check ALLOWED_HOSTS for IPs
    if ip_addresses:
        # Prefer IPs that start with 192.168 or 10. or 172.
        for ip in ip_addresses:
            if ip.startswith(('192.168.', '10.', '172.')):
                return ip
        return ip_addresses[0]
    
    # Last resort: Check ALLOWED_HOSTS for IP addresses
    allowed_hosts = getattr(settings, 'ALLOWED_HOSTS', [])
    for host in allowed_hosts:
        if host and host != '*' and host != 'localhost' and '.' in host:
            try:
                # Check if it's a valid IP
                socket.inet_aton(host)
                if host.startswith(('192.168.', '10.', '172.')):
                    return host
            except:
                pass
    
    # Final fallback
    return '127.0.0.1'


def get_accessible_url(request):
    """Get an accessible URL from request, always using network IP"""
    if not request:
        return None
    
    protocol = 'https' if request.is_secure() else 'http'
    host = request.get_host()
    
    # Extract port from host
    port = '8000'  # Default Django dev port
    if ':' in host:
        parts = host.split(':')
        port = parts[1]
    
    # Check if we have SITE_DOMAIN configured (takes priority)
    domain = getattr(settings, 'SITE_DOMAIN', None)
    if domain:
        use_port = getattr(settings, 'SITE_PORT', '')
        if use_port:
            port = use_port
        
        if port and port not in ['80', '443']:
            return f'{protocol}://{domain}:{port}'
        else:
            return f'{protocol}://{domain}'
    
    # ALWAYS use network IP (never localhost/127.0.0.1)
    # This ensures URLs work from any device on the network
    local_ip = get_local_ip()
    
    # Always include port for development
    if port and port not in ['80', '443']:
        return f'{protocol}://{local_ip}:{port}'
    else:
        return f'{protocol}://{local_ip}'


def send_order_confirmation_email(order, request=None):
    """Send order confirmation email to customer"""
    import sys
    subject = f'Order Confirmed - Medicio'
    
    # Generate tracking token and URL
    token = generate_order_token(order)
    
    # Build tracking URL
    if request:
        tracking_url = request.build_absolute_uri(f'/order/track/{order.id}/{token}/')
    else:
        # Fallback: use settings or default
        domain = getattr(settings, 'SITE_DOMAIN', None)
        if domain:
            protocol = 'https' if getattr(settings, 'USE_HTTPS', False) else 'http'
            port = getattr(settings, 'SITE_PORT', '')
            if port and port not in ['80', '443']:
                tracking_url = f'{protocol}://{domain}:{port}/order/track/{order.id}/{token}/'
            else:
                tracking_url = f'{protocol}://{domain}/order/track/{order.id}/{token}/'
        else:
            tracking_url = f'http://localhost:8000/order/track/{order.id}/{token}/'
    
    # Create the email content
    html_content = f'''
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                line-height: 1.6;
                color: #333;
                max-width: 600px;
                margin: 0 auto;
                padding: 20px;
            }}
            .header {{
                background: linear-gradient(135deg, #3fbbc0 0%, #2a9d9f 100%);
                color: white;
                padding: 30px;
                text-align: center;
                border-radius: 10px 10px 0 0;
            }}
            .header h1 {{
                margin: 0;
                font-size: 28px;
            }}
            .content {{
                background: #f9f9f9;
                padding: 30px;
                border: 1px solid #e0e0e0;
            }}
            .order-details {{
                background: white;
                padding: 20px;
                border-radius: 8px;
                margin: 20px 0;
                border-left: 4px solid #3fbbc0;
            }}
            .order-details h3 {{
                color: #3fbbc0;
                margin-top: 0;
            }}
            .highlight {{
                background: linear-gradient(135deg, #3fbbc0 0%, #2a9d9f 100%);
                color: white;
                padding: 15px 25px;
                border-radius: 8px;
                display: inline-block;
                font-weight: bold;
                font-size: 18px;
            }}
            .delivery-info {{
                background: #fff3cd;
                border: 1px solid #ffc107;
                padding: 15px;
                border-radius: 8px;
                margin: 20px 0;
            }}
            .delivery-info strong {{
                color: #856404;
            }}
            .footer {{
                background: #333;
                color: white;
                padding: 20px;
                text-align: center;
                border-radius: 0 0 10px 10px;
                font-size: 14px;
            }}
            .checkmark {{
                font-size: 50px;
                color: #28a745;
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <div class="checkmark">✓</div>
            <h1>Order Confirmed!</h1>
        </div>
        <div class="content">
            <p>Dear <strong>{order.prenom_client} {order.nom_client}</strong>,</p>
            
            <p>Great news! Your order has been confirmed.</p>
            
            <div class="order-details">
                <h3>📦 Order Details</h3>
                <p><strong>Order ID:</strong> #{order.id}</p>
                <p><strong>Product:</strong> {order.produit.nom}</p>
                <p><strong>Quantity:</strong> {order.quantite}</p>
                <p><strong>Total:</strong> {order.total:.2f} DT</p>
            </div>
            
            <p style="text-align: center;">
                <span class="highlight">{order.quantite} x {order.produit.nom}</span>
            </p>
            
            <div class="delivery-info">
                <strong>🚚 Delivery Information:</strong><br>
                Your order will be delivered within <strong>24-48 hours</strong> to:<br>
                {order.adresse_client}
            </div>
            
            <div class="tracking-link">
                <h3>📱 Track Your Order</h3>
                <p>Click the link below to view your order details:</p>
                <p><a href="{tracking_url}">{tracking_url}</a></p>
            </div>
            
            <p>If you have any questions about your order, please don't hesitate to contact us.</p>
            
            <p>Thank you for shopping with us!</p>
            
            <p>Best regards,<br><strong>The Medicio Team</strong></p>
        </div>
        <div class="footer">
            <p>© 2025 Medicio - All Rights Reserved</p>
            <p>This is an automated message. Please do not reply directly to this email.</p>
        </div>
    </body>
    </html>
    '''
    
    # Plain text version
    plain_message = f'''
    Order Confirmed!
    
    Dear {order.prenom_client} {order.nom_client},
    
    Great news! Your order has been confirmed.
    
    Order Details:
    - Order ID: #{order.id}
    - Product: {order.produit.nom}
    - Quantity: {order.quantite}
    - Total: {order.total:.2f} DT
    
    Your order ({order.quantite} x {order.produit.nom}) is confirmed and will be delivered within 24-48 hours.
    
    Delivery Address: {order.adresse_client}
    
    Track your order: {tracking_url}
    
    Thank you for shopping with us!
    
    Best regards,
    The Medicio Team
    '''
    
    # Create the email
    email = EmailMultiAlternatives(
        subject=subject,
        body=plain_message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[order.email_client],
    )
    email.attach_alternative(html_content, "text/html")
    
    email.send(fail_silently=False)


def health_quiz(request):
    """
    Vue pour le quiz santé avec API
    Montre: Gestion d'erreurs, Session management, User experience
    """
    if request.method == 'POST':
        try:
            # Récupérer les réponses depuis le formulaire
            answers = []
            correct_answers = request.session.get('quiz_correct_answers', [])
            
            # Récupérer les réponses du formulaire
            for i in range(len(correct_answers)):
                answer = request.POST.get(f'question_{i}', None)
                if answer is not None:
                    answers.append(int(answer))
                else:
                    messages.error(request, 'Veuillez répondre à toutes les questions')
                    return redirect('health_quiz')
            
            if len(answers) != len(correct_answers):
                messages.error(request, 'Erreur: nombre de réponses invalide')
                return redirect('health_quiz')
            
            # Calculer le score
            correct_count = sum(1 for i, ans in enumerate(answers) 
                              if ans == correct_answers[i])
            
            # Nettoyer la session des réponses
            request.session.pop('quiz_correct_answers', None)
            
            # Générer coupon si 3/3 correct
            if correct_count == 3:
                code = Coupon.generate_unique_code()
                coupon = Coupon.objects.create(
                    code=code,
                    discount_percent=5.00,
                    expires_at=timezone.now() + timedelta(days=30),
                    max_uses=1,
                    generated_from_quiz=True,
                    quiz_score=3
                )
                
                # NE PAS ajouter l'utilisateur à used_by ici
                # L'utilisateur sera ajouté seulement quand il utilisera le coupon lors du paiement
                
                # Stocker le coupon dans la session
                request.session['coupon_code'] = code
                request.session['quiz_result'] = 'success'
                request.session['quiz_coupon_code'] = code
                request.session['quiz_score'] = 3
                
                return redirect('panier')
            else:
                # Stocker le résultat pour afficher dans le popup
                request.session['quiz_result'] = 'failed'
                request.session['quiz_score'] = correct_count
                return redirect('panier')
                
        except (KeyError, ValueError, TypeError) as e:
            # En cas d'erreur, rediriger vers le panier
            request.session['quiz_result'] = 'error'
            return redirect('panier')
        except Exception as e:
            # Gestion d'erreur générale (ex: problème de base de données)
            request.session['quiz_result'] = 'error'
            return redirect('panier')
    
    # GET: Récupérer questions depuis API ou fallback
    try:
        questions = HealthQuizService.get_questions(3)
        
        if not questions or len(questions) < 3:
            # Si pas assez de questions, rediriger vers le panier
            request.session['quiz_result'] = 'error'
            return redirect('panier')
        
        # Sauvegarder les bonnes réponses en session
        correct_answers = [q['correct_index'] for q in questions]
        request.session['quiz_correct_answers'] = correct_answers
        
        # Préparer les questions pour le template (sans la bonne réponse)
        questions_for_template = []
        for i, q in enumerate(questions):
            questions_for_template.append({
                'id': i,
                'question': q['question'],
                'options': q['options']
            })
        
        return render(request, 'front/products/health_quiz.html', {
            'questions': questions_for_template
        })
    except Exception as e:
        # En cas d'erreur, rediriger vers le panier
        request.session['quiz_result'] = 'error'
        return redirect('panier')


def order_tracking(request, order_id, token):
    """View for order tracking page"""
    order = get_object_or_404(Commande, id=order_id)
    
    # Verify token
    expected_token = generate_order_token(order)
    if token != expected_token:
        return render(request, 'front/products/order_tracking.html', {
            'error': 'Invalid tracking link'
        })
    
    return render(request, 'front/products/order_tracking.html', {
        'order': order
    })


def reject_order(request, order_id):
    """Vue pour refuser une commande"""
    order = get_object_or_404(Commande, id=order_id)
    
    if request.method == 'POST':
        try:
            order.refuser()
            messages.success(request, f'Order #{order.id} rejected!')
        except ValidationError as e:
            messages.error(request, str(e))
    
    return redirect('orders_list')


def products_list(request):
    """Vue pour lister les produits"""
    products = Produit.objects.all()
    
    # Recherche par nom
    search_query = request.GET.get('search', '')
    if search_query:
        products = products.filter(nom__icontains=search_query)
    
    # Filtre par catégorie
    category_filter = request.GET.get('category', '')
    if category_filter:
        products = products.filter(category=category_filter)
    
    # Filtre par date
    date_filter = request.GET.get('date', '')
    if date_filter:
        products = products.filter(date_ajout__date=date_filter)
    
    # Tri par prix
    sort_by = request.GET.get('sort', '')
    if sort_by == 'price_asc':
        products = products.order_by('prix_vente')
    elif sort_by == 'price_desc':
        products = products.order_by('-prix_vente')
    elif sort_by == 'date_asc':
        products = products.order_by('date_ajout')
    elif sort_by == 'date_desc':
        products = products.order_by('-date_ajout')
    else:
        products = products.order_by('-date_ajout')
    
    # Récupérer toutes les catégories pour le filtre
    categories = Produit.CATEGORY_CHOICES
    
    # Ajouter les prédictions de stock pour chaque produit
    products_with_predictions = []
    for product in products:
        stock_status = product.get_stock_status()
        products_with_predictions.append({
            'product': product,
            'stock_status': stock_status,
            'days_until_out': stock_status['days_until_out'],
        })
    
    return render(request, 'back/products/products.html', {
        'products': products,
        'products_with_predictions': products_with_predictions,
        'search_query': search_query,
        'category_filter': category_filter,
        'date_filter': date_filter,
        'sort_by': sort_by,
        'categories': categories,
    })


def product_add(request):
    """Vue pour ajouter un produit"""
    if request.method == 'POST':
        nom = request.POST.get('nom', '').strip()
        description = request.POST.get('description', '').strip()
        prix_achat = request.POST.get('prix_achat')
        prix_vente = request.POST.get('prix_vente')
        category = request.POST.get('category')
        quantite = request.POST.get('quantite', 0)
        image = request.FILES.get('image')
        
        # Validation de base - champs requis
        if not all([nom, prix_achat, prix_vente, category]):
            messages.error(request, 'Please fill in all required fields')
            return redirect('products_list')
        
        # Validation Name - pas de caractères spéciaux
        name_pattern = re.compile(r'^[a-zA-Z0-9\s]+$')
        if not name_pattern.match(nom):
            messages.error(request, 'Name cannot contain special characters')
            return redirect('products_list')
        
        # Validation Description - si fournie, minimum 10 caractères et caractères autorisés uniquement
        if description:
            if len(description) < 10:
                messages.error(request, 'Description must contain at least 10 characters')
                return redirect('products_list')
            # Pattern: lettres, chiffres, espaces, et les caractères autorisés: . / : %
            desc_pattern = re.compile(r'^[a-zA-Z0-9\s./:%]+$')
            if not desc_pattern.match(description):
                messages.error(request, 'Description can only contain letters, numbers, spaces, and these characters: . / : %')
                return redirect('products_list')
        
        # Validation des prix
        try:
            prix_achat_decimal = Decimal(prix_achat)
            prix_vente_decimal = Decimal(prix_vente)
        except (ValueError, TypeError):
            messages.error(request, 'Invalid price format')
            return redirect('products_list')
        
        # Validation Purchase Price - >= 5 DT et ne peut pas être 0
        if prix_achat_decimal <= 0:
            messages.error(request, 'Purchase price cannot be 0')
            return redirect('products_list')
        if prix_achat_decimal < 5:
            messages.error(request, 'Purchase price must be at least 5 DT')
            return redirect('products_list')
        
        # Validation Selling Price - >= 5 DT, ne peut pas être 0, et doit être > Purchase Price
        if prix_vente_decimal <= 0:
            messages.error(request, 'Selling price cannot be 0')
            return redirect('products_list')
        if prix_vente_decimal < 5:
            messages.error(request, 'Selling price must be at least 5 DT')
            return redirect('products_list')
        if prix_vente_decimal <= prix_achat_decimal:
            messages.error(request, 'Selling price must be more than purchase price')
            return redirect('products_list')
        
        # Validation Quantity - doit être > 3
        try:
            quantite_int = int(quantite)
        except (ValueError, TypeError):
            messages.error(request, 'Invalid quantity format')
            return redirect('products_list')
        
        if quantite_int <= 3:
            messages.error(request, 'Quantity must be more than 3')
            return redirect('products_list')
        
        try:
            produit = Produit.objects.create(
                nom=nom,
                description=description if description else '',
                prix_achat=prix_achat_decimal,
                prix_vente=prix_vente_decimal,
                category=category,
                quantite=quantite_int,
                image=image
            )
            messages.success(request, f'Product "{produit.nom}" added successfully!')
            
            # Générer les données historiques et entraîner le modèle en arrière-plan
            # On le fait dans un thread pour ne pas bloquer la réponse
            def train_model_background():
                try:
                    # Générer les données historiques
                    call_command('generate_historical_orders', '--days', '90', verbosity=0)
                    # Entraîner le modèle
                    call_command('train_stock_model', verbosity=0)
                except Exception as e:
                    # Log l'erreur mais ne bloque pas l'ajout du produit
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.error(f"Erreur lors de l'entraînement du modèle ML: {e}")
            
            # Lancer dans un thread séparé
            thread = threading.Thread(target=train_model_background)
            thread.daemon = True
            thread.start()
            
            return redirect('products_list')
        except Exception as e:
            messages.error(request, f'Error adding product: {str(e)}')
    
    return redirect('products_list')


def product_edit(request, product_id):
    """Vue pour modifier un produit"""
    product = get_object_or_404(Produit, id=product_id)
    
    if request.method == 'POST':
        nom = request.POST.get('nom', '').strip()
        description = request.POST.get('description', '').strip()
        prix_achat = request.POST.get('prix_achat')
        prix_vente = request.POST.get('prix_vente')
        category = request.POST.get('category')
        quantite = request.POST.get('quantite')
        
        # Validation de base - champs requis
        if not all([nom, prix_achat, prix_vente, category]):
            messages.error(request, 'Please fill in all required fields')
            return redirect('products_list')
        
        # Validation Name - pas de caractères spéciaux
        name_pattern = re.compile(r'^[a-zA-Z0-9\s]+$')
        if not name_pattern.match(nom):
            messages.error(request, 'Name cannot contain special characters')
            return redirect('products_list')
        
        # Validation Description - si fournie, minimum 10 caractères et caractères autorisés uniquement
        if description:
            if len(description) < 10:
                messages.error(request, 'Description must contain at least 10 characters')
                return redirect('products_list')
            # Pattern: lettres, chiffres, espaces, et les caractères autorisés: . / : %
            desc_pattern = re.compile(r'^[a-zA-Z0-9\s./:%]+$')
            if not desc_pattern.match(description):
                messages.error(request, 'Description can only contain letters, numbers, spaces, and these characters: . / : %')
                return redirect('products_list')
        
        # Validation des prix
        try:
            prix_achat_decimal = Decimal(prix_achat)
            prix_vente_decimal = Decimal(prix_vente)
        except (ValueError, TypeError):
            messages.error(request, 'Invalid price format')
            return redirect('products_list')
        
        # Validation Purchase Price - >= 5 DT et ne peut pas être 0
        if prix_achat_decimal <= 0:
            messages.error(request, 'Purchase price cannot be 0')
            return redirect('products_list')
        if prix_achat_decimal < 5:
            messages.error(request, 'Purchase price must be at least 5 DT')
            return redirect('products_list')
        
        # Validation Selling Price - >= 5 DT, ne peut pas être 0, et doit être > Purchase Price
        if prix_vente_decimal <= 0:
            messages.error(request, 'Selling price cannot be 0')
            return redirect('products_list')
        if prix_vente_decimal < 5:
            messages.error(request, 'Selling price must be at least 5 DT')
            return redirect('products_list')
        if prix_vente_decimal <= prix_achat_decimal:
            messages.error(request, 'Selling price must be more than purchase price')
            return redirect('products_list')
        
        # Validation Quantity - doit être > 3
        try:
            quantite_int = int(quantite)
        except (ValueError, TypeError):
            messages.error(request, 'Invalid quantity format')
            return redirect('products_list')
        
        if quantite_int <= 3:
            messages.error(request, 'Quantity must be more than 3')
            return redirect('products_list')
        
        # Mettre à jour le produit
        product.nom = nom
        product.description = description if description else ''
        product.prix_achat = prix_achat_decimal
        product.prix_vente = prix_vente_decimal
        product.category = category
        product.quantite = quantite_int
        
        if 'image' in request.FILES:
            product.image = request.FILES['image']
        
        try:
            product.save()
            messages.success(request, f'Product "{product.nom}" updated successfully!')
            return redirect('products_list')
        except Exception as e:
            messages.error(request, f'Error updating product: {str(e)}')
    
    return redirect('products_list')


def product_delete(request, product_id):
    """Vue pour supprimer un produit"""
    product = get_object_or_404(Produit, id=product_id)
    
    if request.method == 'POST':
        product_name = product.nom
        product.delete()
        messages.success(request, f'Product "{product_name}" deleted successfully!')
    
    return redirect('products_list')


def product_detail(request, product_id):
    """Vue pour afficher les détails d'un produit"""
    produit = get_object_or_404(Produit, id=product_id)
    
    # Compter les articles dans le panier
    panier = request.session.get('panier', {})
    nombre_articles = sum(item['quantite'] for item in panier.values())
    
    # Produits similaires (même catégorie)
    similar_products = Produit.objects.filter(category=produit.category).exclude(id=product_id)[:4]
    
    return render(request, 'front/products/product_detail.html', {
        'produit': produit,
        'nombre_articles_panier': nombre_articles,
        'similar_products': similar_products,
    })


def export_orders_pdf(request):
    """Generate a PDF with all orders"""
    # Create the HttpResponse object with PDF headers
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="orders_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf"'
    
    # Create the PDF buffer
    buffer = BytesIO()
    
    # Create the PDF document with landscape orientation for more width
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4), rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    elements = []
    
    # Styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        spaceAfter=30,
        alignment=TA_CENTER,
        textColor=colors.HexColor('#3fbbc0')
    )
    subtitle_style = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Normal'],
        fontSize=12,
        spaceAfter=20,
        alignment=TA_CENTER,
        textColor=colors.grey
    )
    # Style for table cells that need text wrapping
    cell_style = ParagraphStyle(
        'CellStyle',
        parent=styles['Normal'],
        fontSize=8,
        leading=10,
    )
    
    # Title
    elements.append(Paragraph("Orders Report", title_style))
    elements.append(Paragraph(f"Generated on: {datetime.now().strftime('%B %d, %Y at %H:%M')}", subtitle_style))
    elements.append(Spacer(1, 20))
    
    # Get all orders
    orders = Commande.objects.all().order_by('-date_creation')
    
    if orders.exists():
        # Table header
        table_data = [
            ['Order ID', 'Product', 'Customer', 'Qty', 'Total', 'Status', 'Date', 'Phone', 'Address']
        ]
        
        # Add order data
        for order in orders:
            # Use full address with Paragraph for text wrapping
            address = order.adresse_client or 'N/A'
            address_para = Paragraph(address, cell_style)
            
            # Format status
            status_map = {
                'en_attente': 'Pending',
                'acceptee': 'Accepted',
                'refusee': 'Rejected'
            }
            status = status_map.get(order.statut, order.statut)
            
            # Use Paragraph for product and customer names too for better wrapping
            product_para = Paragraph(order.produit.nom, cell_style)
            customer_para = Paragraph(f'{order.prenom_client or ""} {order.nom_client or ""}', cell_style)
            
            table_data.append([
                f'#{order.id}',
                product_para,
                customer_para,
                str(order.quantite),
                f'{order.total:.2f} DT',
                status,
                order.date_creation.strftime('%Y-%m-%d'),
                order.telephone_client or 'N/A',
                address_para
            ])
        
        # Create table with adjusted column widths for landscape (total width ~780 for A4 landscape)
        col_widths = [50, 100, 100, 35, 65, 60, 70, 75, 130]
        table = Table(table_data, colWidths=col_widths)
        
        # Table styling
        table_style = TableStyle([
            # Header styling
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3fbbc0')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('VALIGN', (0, 0), (-1, 0), 'MIDDLE'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('TOPPADDING', (0, 0), (-1, 0), 12),
            
            # Data rows styling
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
            ('ALIGN', (0, 1), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 1), (-1, -1), 'MIDDLE'),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('TOPPADDING', (0, 1), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 10),
            ('LEFTPADDING', (0, 1), (-1, -1), 5),
            ('RIGHTPADDING', (0, 1), (-1, -1), 5),
            
            # Alternating row colors
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
            
            # Grid
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#dee2e6')),
            ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#3fbbc0')),
            
            # Left align for text columns (Product, Customer, Address)
            ('ALIGN', (1, 1), (2, -1), 'LEFT'),
            ('ALIGN', (8, 1), (8, -1), 'LEFT'),
        ])
        
        # Add conditional formatting for status column
        for i, order in enumerate(orders, start=1):
            if order.statut == 'acceptee':
                table_style.add('TEXTCOLOR', (5, i), (5, i), colors.HexColor('#28a745'))
            elif order.statut == 'refusee':
                table_style.add('TEXTCOLOR', (5, i), (5, i), colors.HexColor('#dc3545'))
            elif order.statut == 'en_attente':
                table_style.add('TEXTCOLOR', (5, i), (5, i), colors.HexColor('#ffc107'))
        
        table.setStyle(table_style)
        elements.append(table)
        
        # Summary section
        elements.append(Spacer(1, 30))
        
        summary_style = ParagraphStyle(
            'Summary',
            parent=styles['Normal'],
            fontSize=10,
            spaceAfter=5,
        )
        
        total_orders = orders.count()
        pending = orders.filter(statut='en_attente').count()
        accepted = orders.filter(statut='acceptee').count()
        rejected = orders.filter(statut='refusee').count()
        total_revenue = sum(order.total for order in orders.filter(statut='acceptee'))
        
        elements.append(Paragraph(f"<b>Summary:</b>", summary_style))
        elements.append(Paragraph(f"Total Orders: {total_orders}", summary_style))
        elements.append(Paragraph(f"Pending: {pending} | Accepted: {accepted} | Rejected: {rejected}", summary_style))
        elements.append(Paragraph(f"Total Revenue (Accepted Orders): {total_revenue:.2f} DT", summary_style))
        
    else:
        no_data_style = ParagraphStyle(
            'NoData',
            parent=styles['Normal'],
            fontSize=14,
            alignment=TA_CENTER,
            textColor=colors.grey
        )
        elements.append(Spacer(1, 100))
        elements.append(Paragraph("No orders found.", no_data_style))
    
    # Build PDF
    doc.build(elements)
    
    # Get the value of the BytesIO buffer and write it to the response
    pdf = buffer.getvalue()
    buffer.close()
    response.write(pdf)
    
    return response
