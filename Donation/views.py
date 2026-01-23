from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from .models import Donation
from UserApp.models import User
from Publication.models import Publication
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy,reverse
from .forms import DonationForm
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib import messages
from django.utils import timezone
from datetime import date
from django.utils import timezone
from datetime import timedelta
import stripe
from django.db.models import Q
from twilio.rest import Client
from django.conf import settings
from Donation.models import DonorBadge, TelegramLink
from django.db.models import Sum
from django.utils.decorators import method_decorator
from UserApp.decorators import role_required
from Clinica.utils.telegram_bot import send_telegram_message



# ========== VUES BACKEND (ADMIN) ==========

class AdminDonationListView(ListView):
    model = Donation
    context_object_name = 'donations'
    template_name = 'Back/Donation/donation_list.html'
    paginate_by = 10

    def get_queryset(self):
        qs = Donation.objects.select_related("id_user", "id_publication").all()

        search = self.request.GET.get("search")
        sort = self.request.GET.get("sort")
        date_filter = self.request.GET.get("date")

        # --- SEARCH ---
        if search:
            qs = qs.filter(
                Q(id_user__first_name__icontains=search) |
                Q(id_user__last_name__icontains=search) |
                Q(id_user__email__icontains=search)
            )

        # --- FILTER BY DATE ---
        if date_filter:
            qs = qs.filter(date_donation__date=date_filter)

        # --- SORT ---
        if sort == "date_asc":
            qs = qs.order_by("date_donation")
        elif sort == "date_desc":
            qs = qs.order_by("-date_donation")
        elif sort == "amount_asc":
            qs = qs.order_by("montant")
        elif sort == "amount_desc":
            qs = qs.order_by("-montant")
        else:
            qs = qs.order_by("-date_donation")

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Garder les filtres dans la pagination
        params = self.request.GET.copy()
        if "page" in params:
            params.pop("page")
        context["querystring"] = params.urlencode()

        # Statistiques sidebar
        all_donations = Donation.objects.all()
        context["money_count"] = all_donations.filter(type_donation='argent').count()
        context["volunteer_count"] = all_donations.filter(type_donation='volontariat').count()
        context["pending_count"] = all_donations.filter(statut='en_attente').count()

        return context
    

class AdminDonationDetailView(DetailView):
    model = Donation
    template_name = 'Back/Donation/donation_detail.html'
    context_object_name = 'donation'
    
    
class AdminDonationDeleteView(DeleteView):
    model = Donation
    success_url = reverse_lazy('donation:admin_donation_list')
    template_name = 'Back/Donation/donation_confirm_delete.html'
    

# ========== VUES FRONTEND (USER) ==========
@method_decorator( role_required('nurse', 'doctor', 'intern', 'user', 'patient'),
    name='dispatch')
class FrontPublicationListView(ListView):
    model = Publication
    context_object_name = 'publications'
    template_name = 'Front/Donation/donations_page.html'
    paginate_by = 12
    
    def get_queryset(self):
        from django.utils import timezone
        return Publication.objects.filter(deadline__gte=timezone.now().date())
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Publications dans les 10 prochains jours
        today = timezone.now().date()
        ten_days_later = today + timedelta(days=10)
        
        context['upcoming_publications'] = Publication.objects.filter(
            deadline__gte=today,
            deadline__lte=ten_days_later
        ).order_by('deadline')[:3]  # Limité à 3 publications
        
        return context

class FrontPublicationDetailView(DetailView):
    model = Publication
    template_name = 'Front/Publication/publication_detail.html'
    context_object_name = 'publication'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Ajouter les donations liées à cette publication
        context['donations'] = self.object.donations.all()
        context['total_argent'] = sum(
            d.montant for d in self.object.donations.filter(type_donation='argent', statut='valide') 
            if d.montant
        )
        context['nombre_volontaires'] = self.object.donations.filter(
            type_donation='volontariat', statut='valide'
        ).count()
        return context



from django.core.paginator import Paginator

def donation_create(request):
    donations = Donation.objects.filter(user=request.user).order_by('-id')
    
    paginator = Paginator(donations, 4)   # 4 cards par page
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    return render(request, "donation_create.html", {
        "user_donations": page_obj,
        "page_obj": page_obj,
    })


stripe.api_key = settings.STRIPE_SECRET_KEY
@method_decorator( role_required('Nurse', 'Doctor', 'Intern', 'User', 'Patient'),
    name='dispatch')
class FrontDonationCreateView(LoginRequiredMixin, CreateView):
    model = Donation
    form_class = DonationForm
    template_name = 'Front/Donation/donation_create.html'
    login_url = 'login'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        publication_id = self.request.GET.get('publication')
        if publication_id:
            kwargs['publication_id'] = publication_id
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        publication_id = self.request.GET.get('publication')
        if publication_id:
            try:
                context['publication'] = Publication.objects.get(pk=publication_id)
            except Publication.DoesNotExist:
                pass

        context['user_donations'] = Donation.objects.filter(
            id_user=self.request.user
        ).select_related('id_publication').order_by('-date_donation')

        # === MES BADGES ===
        context['badges'] = DonorBadge.objects.filter(user=self.request.user)
        
        return context

    def form_valid(self, form):
        # On complète l'objet mais on ne le sauvegarde pas tout de suite
        donation = form.save(commit=False)
        donation.id_user = self.request.user

        # --- Tes validations serveur ---
        if donation.type_donation == 'argent':
            if not donation.montant or donation.montant <= 0:
                form.add_error('montant', 'Le montant doit être supérieur à 0')
                return self.form_invalid(form)
            if not donation.methode_paiement:
                form.add_error('methode_paiement', 'Veuillez choisir une méthode de paiement')
                return self.form_invalid(form)
        else:  # volontariat
            if not donation.description:
                form.add_error('description', 'Veuillez décrire votre contribution')
                return self.form_invalid(form)

        # Statut par défaut
        donation.statut = 'en_attente'
        donation.save()
        self.object = donation  # pour get_success_url si besoin

        # 🔹 Si c’est un don en argent payé par Stripe → redirection vers Checkout
        if donation.type_donation == 'argent' and donation.methode_paiement == 'stripe':
            return redirect('donation:create_checkout_session', donation_id=donation.id_donation)

        # Sinon, flux normal (espèce, virement, volontariat…)
        messages.success(self.request, "✅ Votre donation a été enregistrée avec succès!")
        return redirect(self.get_success_url())

    def get_success_url(self):
        publication_id = self.object.id_publication.id
        return reverse_lazy('donation:donation_create') + f'?publication={publication_id}'


class UserDonationListView(LoginRequiredMixin, ListView):
    model = Donation
    context_object_name = 'donations'
    template_name = 'Front/Donation/my_donations.html'
    paginate_by = 10
    login_url = 'loginFront'
    
    def get_queryset(self):
        return Donation.objects.filter(id_user=self.request.user).select_related('id_publication')

class UserDonationDeleteView( DeleteView):
    model = Donation
    success_url = reverse_lazy('donation:donation_create')
    template_name = 'Front/Donation/donation_confirm_delete.html'

    
    def get_queryset(self):
        return Donation.objects.filter(id_user=self.request.user)
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, "Votre donation a été supprimée.")
        return super().delete(request, *args, **kwargs)

class FrontPublicationDetailView(DetailView):
    model = Publication
    template_name = 'Front/Publication/publication_detail.html'
    context_object_name = 'publication'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get donations for this publication
        donations = self.object.donations.filter(statut='valide')
        
        # Calculate participants
        context['nb_participants'] = donations.count()
        
        # Calculate total amount
        total = sum(
            d.montant for d in donations.filter(type_donation='argent') 
            if d.montant
        )
        context['total_amount'] = total
        
        # Calculate days remaining
        today = date.today()
        if self.object.deadline >= today:
            context['days_remaining'] = (self.object.deadline - today).days
        else:
            context['days_remaining'] = 0
        
        return context
    


from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from Publication.models import Publication
from Donation.models import Donation
from django.db.models import Sum
from django.utils import timezone  # ← Mets l'import en haut



def back_index(request):
    # Publications stats
    publications = Publication.objects.all()
    total_publications = publications.count()
    recent_publications = publications.order_by('-date_pub')[:5]
    
    # Calcul publications actives vs expirées
    today = timezone.now().date()
    active_publications = publications.filter(deadline__gte=today).count()
    expired_publications = publications.filter(deadline__lt=today).count()
    
    # Donations stats
    donations = Donation.objects.all()
    total_donations = donations.count()
    money_count = donations.filter(type_donation='argent').count()
    volunteer_count = donations.filter(type_donation='volontariat').count()
    pending_count = donations.filter(statut='en_attente').count()
    recent_donations = donations.order_by('-date_donation')[:5]
    
    # Total money received
    total_money_received = donations.filter(
        type_donation='argent',
        statut='valide'
    ).aggregate(total=Sum('montant'))['total'] or 0
    
    context = {
        # ← AJOUT ICI !
        'donations': donations,

        'total_publications': total_publications,
        'active_publications': active_publications,
        'expired_publications': expired_publications,
        'publication_stats': True,
        
        'total_donations': total_donations,
        'money_count': money_count,
        'volunteer_count': volunteer_count,
        'pending_count': pending_count,
        
        'recent_publications': recent_publications,
        'recent_donations': recent_donations,
        
        'donation_stats': True,
        'total_money_received': total_money_received,
    }
    
    return render(request, 'Back/Donation/dashboardDonation.html', context)

#stripe

from django.conf import settings

@login_required
def donation_payment(request, pub_id):
    stripe.api_key = settings.STRIPE_SECRET_KEY
    publication = Publication.objects.get(pk=pub_id)
    # Définit le montant, ici 10€ (à personnaliser !)
    montant = 1000  # en centimes
    payment_intent = stripe.PaymentIntent.create(
        amount=montant,
        currency='eur',
        metadata={'pub_id': pub_id, 'user_id': request.user.id}
    )
    # On donne la clé publique Stripe + le client_secret du PaymentIntent au template
    context = {
        "stripe_public_key": settings.STRIPE_PUBLISHABLE_KEY,
        "client_secret": payment_intent.client_secret,
        "pub_id": pub_id,
        "montant": montant/100,  # Pour l'affichage
        "publication": publication,
    }
    return render(request, "donation/donation_payment.html", context)



from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse



@csrf_exempt
def create_payment_intent(request):
    if request.method == 'POST':
        montant = float(request.POST.get("montant", "0"))
        if montant < 1:
            return JsonResponse({"error": "Montant non valide"}, status=400)
        import stripe
        from django.conf import settings
        stripe.api_key = settings.STRIPE_SECRET_KEY
        payment_intent = stripe.PaymentIntent.create(
            amount=int(montant * 100),
            currency='eur',
        )
        return JsonResponse({
            "client_secret": payment_intent.client_secret,
            "stripe_public_key": settings.STRIPE_PUBLISHABLE_KEY,
        })
    return JsonResponse({'error': 'Bad request'}, status=400)


from django.http import Http404

@login_required
def create_checkout_session(request, donation_id):
    donation = get_object_or_404(Donation, pk=donation_id, id_user=request.user)

    # Montant en CENTIMES (Stripe travaille en cents)
    amount_cents = int(donation.montant * 100)

    try:
        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            mode='payment',
            line_items=[{
                'price_data': {
                    'currency': 'usd',  # ou 'eur' (TND n'est pas supporté par Stripe)
                    'product_data': {
                        'name': f"Donation Clinica+ #{donation.id_donation}",
                    },
                    'unit_amount': amount_cents,
                },
                'quantity': 1,
            }],
            success_url = request.build_absolute_uri(
             reverse('donation:stripe_success', args=[donation.id_donation])),

            cancel_url=request.build_absolute_uri(
                reverse('donation:stripe_cancel', args=[donation.id_donation])
            ),
        )
    except Exception as e:
        messages.error(request, f"Erreur Stripe : {e}")
        # Retour à la page de don
        return redirect('donation:donation_create') + f'?publication={donation.id_publication.id}'

    # Redirection vers la page hébergée par Stripe (celle de ta capture)
    return redirect(session.url, code=303)


def award_badges(user):
    """Attribue automatiquement les badges selon les dons de l'utilisateur."""

    # Nombre total de dons validés
    total_dons = Donation.objects.filter(
        id_user=user, statut="valide"
    ).count()

    # Total argent donné
    total_money = Donation.objects.filter(
        id_user=user, statut="valide", type_donation="argent"
    ).aggregate(total=Sum("montant"))["total"] or 0

    badges_to_give = []

    if total_dons >= 3:
        badges_to_give.append("bronze")
    if total_dons >= 10:
        badges_to_give.append("silver")
    if total_dons >= 20:
        badges_to_give.append("gold")
    if total_money >= 500:
        badges_to_give.append("hero")

    # Ajouter les badges manquants
    for b in badges_to_give:
        DonorBadge.objects.get_or_create(user=user, badge=b)


@login_required
def stripe_success(request, donation_id):
    donation = get_object_or_404(Donation, pk=donation_id, id_user=request.user)

    # Valider donation
    donation.statut = 'valide'
    donation.save()

    # Badges
    award_badges(request.user)

    # Check Telegram link
    link = TelegramLink.objects.filter(user=request.user).first()
    telegram_linked = bool(link and link.chat_id)

    # Send Telegram message
    if telegram_linked:
        send_telegram_message(
            link.chat_id,
            f"🎉 Thank you {request.user.first_name}!\n\n"
            f"Your donation for « {donation.id_publication.title} » has been confirmed with success❤\n"
            f"Amount: {donation.montant} DT"
        )

    return render(
        request,
        'Front/Donation/success_paymentD.html',
        {
            "donation": donation,
            "telegram_linked": telegram_linked
        }
    )



@login_required
def stripe_cancel(request, donation_id):
    donation = get_object_or_404(Donation, pk=donation_id, id_user=request.user)
    donation.statut = 'echec'
    donation.save()
    messages.error(request, "Le paiement Stripe a été annulé.")

    url = reverse('donation:donation_create') + f'?publication={donation.id_publication.id}'
    return redirect(url)



#twilio
import json
from django.core import signing
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import get_user_model
from .models import TelegramLink, Donation
from Clinica.utils.telegram_bot import send_telegram_message
from django.conf import settings
import random
import string
User = get_user_model()

@login_required
def telegram_connect(request):
    # Générer un token court
    short = ''.join(random.choices("0123456789", k=6))

    TelegramLink.objects.update_or_create(
        user=request.user,
        defaults={"short_token": short}
    )

    bot = settings.TELEGRAM_BOT_USERNAME
    url = f"https://t.me/{bot}?start={short}"

    return redirect(url)


@csrf_exempt
def telegram_webhook(request, secret):
    if secret != settings.TELEGRAM_WEBHOOK_SECRET:
        return JsonResponse({"ok": True})

    try:
        update = json.loads(request.body.decode("utf-8"))
    except:
        return JsonResponse({"ok": True})

    message = update.get("message", {})
    text = (message.get("text") or "").strip()
    chat_id = (message.get("chat") or {}).get("id")

    # ========== COMMANDES ==========
    
    # /help
    if text == "/help":
        send_telegram_message(chat_id,
            "📘 Commandes disponibles :\n"
            "/help - Aide\n"
            "/mydonations - Voir vos donations\n"
            "/last - Dernière donation\n"
            "/badges - Vos badges\n"
            "/stop - Déconnecter Telegram"
        )
        return JsonResponse({"ok": True})

    # /stop
    if text == "/stop":
        TelegramLink.objects.filter(chat_id=str(chat_id)).delete()
        send_telegram_message(chat_id, "🛑 Vous êtes déconnecté de Clinica+.")
        return JsonResponse({"ok": True})

    # /mydonations
    if text == "/mydonations":
        link = TelegramLink.objects.filter(chat_id=str(chat_id)).first()
        if not link:
            send_telegram_message(chat_id, "❌ Vous n'êtes pas connecté.")
            return JsonResponse({"ok": True})

        dons = Donation.objects.filter(id_user=link.user).order_by("-date_donation")[:5]

        if not dons:
            send_telegram_message(chat_id, "🔍 Aucun don trouvé.")
            return JsonResponse({"ok": True})

        msg = "🧾 Vos 5 derniers dons :\n\n"
        for d in dons:
            msg += f"• {d.id_publication.title} — {d.montant} USD\n"

        send_telegram_message(chat_id, msg)
        return JsonResponse({"ok": True})

    # /last
    if text == "/last":
        link = TelegramLink.objects.filter(chat_id=str(chat_id)).first()
        if not link:
            send_telegram_message(chat_id, "❌ Vous n'êtes pas connecté.")
            return JsonResponse({"ok": True})

        last = Donation.objects.filter(id_user=link.user).order_by("-date_donation").first()

        if not last:
            send_telegram_message(chat_id, "❌ Aucun don trouvé.")
            return JsonResponse({"ok": True})

        send_telegram_message(
            chat_id,
            f"📌 Dernière donation :\n"
            f"Publication : {last.id_publication.title}\n"
            f"Montant : {last.montant} USD\n"
            f"Date : {last.date_donation.strftime('%d/%m/%Y')}"
        )
        return JsonResponse({"ok": True})

    # /badges
    if text == "/badges":
        link = TelegramLink.objects.filter(chat_id=str(chat_id)).first()
        if not link:
            send_telegram_message(chat_id, "❌ Vous n'êtes pas connecté.")
            return JsonResponse({"ok": True})

        badges = DonorBadge.objects.filter(user=link.user)

        if not badges:
            send_telegram_message(chat_id, "🏅 Aucun badge pour le moment.")
            return JsonResponse({"ok": True})

        msg = "🏅 Vos badges :\n\n"
        for b in badges:
            msg += f"• {b.get_badge_display()} 🎖️\n"

        send_telegram_message(chat_id, msg)
        return JsonResponse({"ok": True})

    # /start <short_token>
    if text.startswith("/start"):
        parts = text.split(" ", 1)

        if len(parts) == 2:
            short = parts[1].strip()

            link = TelegramLink.objects.filter(short_token=short).first()

            if link:
                link.chat_id = str(chat_id)
                link.save()
                send_telegram_message(chat_id, "✅ Clinica+ connecté à Telegram !")
            else:
                send_telegram_message(chat_id, "❌ Code invalide. Réessayez depuis Clinica+.")

        return JsonResponse({"ok": True})

    return JsonResponse({"ok": True})


from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.lib import colors
from io import BytesIO
from django.http import HttpResponse
from datetime import datetime
from .models import Donation


def export_donations_pdf(request):
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="donations_report.pdf"'

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4))
    elements = []

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'Title', parent=styles['Heading1'], fontSize=24,
        textColor=colors.HexColor("#3fbbc0"),
        alignment=TA_CENTER,
        spaceAfter=20
    )

    cell_style = ParagraphStyle(
        'Cell', parent=styles['Normal'],
        fontSize=9, leading=11
    )

    # ----------- TITLE -------------
    elements.append(Paragraph("Clinica+ — Donations Report", title_style))
    elements.append(Paragraph(
        f"Generated on: {datetime.now().strftime('%d %B %Y - %H:%M')}",
        styles["Normal"]
    ))
    elements.append(Spacer(1, 15))

    donations = Donation.objects.select_related("id_user", "id_publication") \
                                .order_by('-date_donation')

    # TABLE HEADER
    data = [["ID", "Donor", "Publication", "Type", "Amount",
             "Description", "Status", "Date"]]

    # ----------- TABLE ROWS ----------
    for d in donations:
        donor = f"{d.id_user.first_name} {d.id_user.last_name}" \
            if (d.id_user.first_name or d.id_user.last_name) else d.id_user.email

        donor_para = Paragraph(donor, cell_style)
        pub_para = Paragraph(d.id_publication.title, cell_style)
        desc_para = Paragraph(d.description if d.description else "—", cell_style)

        type_label = "Money" if d.type_donation == "argent" else "Volunteer"
        amount = f"{d.montant} DT" if d.type_donation == "argent" else "—"

        # STATUS COLOR LOGIC
        status_map = {
            'en_attente': "Pending",
            'valide': "Approved",
            'echec': "Rejected"
        }

        if d.statut == "valide":
            status_color = "green"
        elif d.statut == "echec":
            status_color = "red"
        else:
            status_color = "orange"

        status_text = status_map.get(d.statut, d.statut)

        status_para = Paragraph(
            f'<font color="{status_color}"><b>{status_text}</b></font>',
            cell_style
        )

        # ADD ROW TO TABLE
        data.append([
            str(d.id_donation),
            donor_para,
            pub_para,
            type_label,
            amount,
            desc_para,
            status_para,
            d.date_donation.strftime("%Y-%m-%d %H:%M")
        ])

    # ----------- TABLE STYLE ----------
    table = Table(data, colWidths=[40, 120, 120, 60, 60, 180, 70, 80])

    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#3fbbc0")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 10),

        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('VALIGN', (0, 1), (-1, -1), 'MIDDLE'),
        ('ALIGN', (0, 1), (0, -1), 'CENTER'),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
    ]))

    elements.append(table)

    # ----------- SUMMARY SECTION ----------
    elements.append(Spacer(1, 30))

    summary_title = Paragraph(
        "<b>Summary:</b>",
        ParagraphStyle(
            'SummaryTitle', parent=styles['Heading2'], fontSize=14,
            textColor=colors.HexColor("#3fbbc0"), spaceAfter=10
        )
    )
    elements.append(summary_title)

    total_donations = donations.count()
    money_donations = donations.filter(type_donation='argent').count()
    volunteer_donations = donations.filter(type_donation='volontariat').count()

    validated = donations.filter(statut='valide').count()
    pending = donations.filter(statut='en_attente').count()
    rejected = donations.filter(statut='echec').count()

    total_money = sum(d.montant for d in donations.filter(type_donation='argent'))

    summary_style = ParagraphStyle(
        'SummaryText', parent=styles['Normal'], fontSize=11, leading=14
    )

    elements.append(Paragraph(f"Total Donations: <b>{total_donations}</b>", summary_style))
    elements.append(Paragraph(
        f"Money Donations: <b>{money_donations}</b>  |  Volunteer Donations: <b>{volunteer_donations}</b>",
        summary_style
    ))
    elements.append(Paragraph(
        f"Validated: <b>{validated}</b>  |  Pending: <b>{pending}</b>  |  Rejected: <b>{rejected}</b>",
        summary_style
    ))
    elements.append(Paragraph(
        f"Total Money Donated: <b>{total_money:.2f} DT</b>",
        summary_style
    ))

    # ----------- EXPORT PDF ----------
    doc.build(elements)
    pdf = buffer.getvalue()
    buffer.close()
    response.write(pdf)

    return response


from django.shortcuts import render, get_object_or_404
from .models import Donation

def donation_receipt(request, donation_id):
    donation = get_object_or_404(Donation, id_donation=donation_id)

    return render(request, "Front/Donation/donation_receipt.html", {
    "donation": donation
    })

from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import A4
from reportlab.lib.enums import TA_CENTER
from reportlab.lib import colors
from reportlab.pdfgen.canvas import Canvas
from django.http import HttpResponse
from io import BytesIO
from datetime import datetime
from django.shortcuts import get_object_or_404
from .models import Donation

def donation_receipt_pdf(request, donation_id):
    donation = get_object_or_404(Donation, id_donation=donation_id)

    buffer = BytesIO()
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="receipt_{donation_id}.pdf"'

    doc = SimpleDocTemplate(buffer, pagesize=A4,
                            leftMargin=40, rightMargin=40, topMargin=40, bottomMargin=40)
    elements = []

    styles = getSampleStyleSheet()

    # -------- TITLE --------
    title_style = ParagraphStyle(
        'Title',
        parent=styles['Heading1'],
        fontSize=26,
        textColor=colors.HexColor("#3fbbc0"),
        alignment=TA_CENTER,
        spaceAfter=25
    )

    elements.append(Paragraph("Clinica+ — Donation Receipt", title_style))
    elements.append(Spacer(1, 15))

    # -------- STATUS BADGE --------
    status_map = {
        'valide': ('Approved', colors.green),
        'echec': ('Failed', colors.red),
        'en_attente': ('Pending', colors.orange)
    }

    status_label, status_color = status_map.get(donation.statut, ("Unknown", colors.black))

    badge_style = ParagraphStyle(
        'Badge',
        parent=styles['Normal'],
        textColor=status_color,
        alignment=TA_CENTER,
        fontSize=14,
        spaceAfter=20
    )

    elements.append(Paragraph(f"<b>Status: {status_label}</b>", badge_style))

    # -------- TABLE --------
    table_data = [
        ["Donation ID", str(donation.id_donation)],
        ["Donor", f"{donation.id_user.first_name} {donation.id_user.last_name}"],
        ["Publication", donation.id_publication.title],
        ["Type", donation.type_donation.capitalize()],
        ["Amount", f"{donation.montant} DT" if donation.type_donation == "argent" else "—"],
        ["Description", donation.description or "—"],
        ["Date", donation.date_donation.strftime("%Y-%m-%d %H:%M")],
    ]

    table = Table(table_data, colWidths=[130, 320])

    table.setStyle(TableStyle([
        # Header background
        ('BACKGROUND', (0, 0), (1, 0), colors.HexColor('#3fbbc0')),
        ('TEXTCOLOR', (0, 0), (1, 0), colors.white),
        ('FONTNAME', (0, 0), (1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (1, 0), 12),

        # Background rows
        ('BACKGROUND', (0, 1), (1, -1), colors.whitesmoke),

        # Borders
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),

        # Alignment
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (1, -1), 10),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('RIGHTPADDING', (0, 0), (-1, -1), 10),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))

    elements.append(table)
    elements.append(Spacer(1, 35))

    # -------- FOOTER --------
    footer_style = ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        alignment=TA_CENTER,
        fontSize=10,
        textColor=colors.grey
    )

    elements.append(Paragraph("Thank you for supporting Clinica+ ❤️", footer_style))
    elements.append(Paragraph(datetime.now().strftime("%d %B %Y - %H:%M"), footer_style))

    doc.build(elements)

    pdf = buffer.getvalue()
    buffer.close()
    response.write(pdf)

    return response
