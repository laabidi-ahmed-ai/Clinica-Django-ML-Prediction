import threading
import ssl
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import EmailMessage, get_connection
from django.contrib.auth import get_user_model
from django.conf import settings
from django.urls import reverse
from django.contrib.sites.models import Site

from cloudinary.uploader import upload as cloudinary_upload
from .models import Publication

User = get_user_model()


def async_send(subject, message, html_message, recipients):

    tls_context = ssl.create_default_context()

    connection = get_connection(
        host=settings.EMAIL_HOST,
        port=settings.EMAIL_PORT,
        username=settings.EMAIL_HOST_USER,
        password=settings.EMAIL_HOST_PASSWORD,
        use_tls=True,
        use_ssl=False,
        timeout=20
    )

    connection.ssl_context = tls_context

    email = EmailMessage(
        subject=subject,
        body=html_message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=recipients,
        connection=connection
    )
    email.content_subtype = "html"

    threading.Thread(target=email.send).start()


@receiver(post_save, sender=Publication)
def send_publication_email_to_users(sender, instance, created, **kwargs):

    if not created:
        return

    # Récupérer emails utilisateurs
    emails = list(
        User.objects.exclude(email__isnull=True)
                    .exclude(email="")
                    .values_list("email", flat=True)
    )
    if not emails:
        return

    # Domaine actuel (Site Framework)
    current_site = Site.objects.get_current()
    base_url = f"https://{current_site.domain}"

    # Upload Cloudinary
    image_url = ""
    if instance.pubPicture:
        result = cloudinary_upload(instance.pubPicture.path)
        image_url = result.get("secure_url")

    # Infos publication
    titre = instance.title
    description = instance.description or "No description"
    deadline = instance.deadline

    # URL absolue de la publication
    publication_url = base_url + reverse("donation:front_publication_detail", args=[instance.id])


    sujet = f"🆕 New Donation Campaign: {titre}"

    # HTML email
    html_message = f"""
<div style="background:#f6f9fc;padding:40px 0;font-family:Arial, sans-serif;">

  <div style="max-width:700px;margin:auto;background:white;border-radius:16px;padding:40px;box-shadow:0 4px 20px rgba(0,0,0,0.08);">

    <!-- HEADER LOGO -->
<div style="text-align:center;margin-top:10px;margin-bottom:10px;">
    <img src="https://res.cloudinary.com/dl7qbkam5/image/upload/v1764293976/logo_site_kjlvuh.png"
         alt="Clinica+ Logo"
         style="width:95px; margin-bottom:10px;">
</div>

<!-- TITLE -->
<h2 style="color:#2a9d9f;text-align:center;font-size:26px;margin:0;">
    🎉 New Event Alert!
</h2>

<!-- BLUE LINE (short, centered) -->
<div style="
    width:650px;
    height:2px;
    background:#2a9d9f;
    margin:10px auto 25px auto;
    border-radius:4px;">
</div>


    <!-- INTRO -->
    <p style="font-size:15px;color:#333;">
        Hello,
        <br ><br>
        We're excited to inform you that a new event has just been published on <strong>Clinica+</strong>:
    </p>

    <!-- EVENT CARD -->
    <div style="background:#eafaf7;padding:25px;border-radius:14px;margin-top:20px;">
        
        <!-- EVENT IMAGE -->
       <div style="background:#eafaf7;padding:20px;border-radius:12px;display:flex;align-items:center;">
            {f"<img src='{image_url}' style='width:120px;border-radius:10px;margin-right:20px;'>" if image_url else ""}
            <p style="font-size:15px;white-space:normal;word-wrap:break-word;word-break:break-word;margin:0;">
                📝 <strong>Title:</strong> {titre}<br><br>
                📄 <strong>Description:</strong> {description}<br><br>
                📅 <strong>Date:</strong> {deadline}<br><br>
                📍 <strong>Location:</strong> {instance.address}<br><br>
            </p>
        </div>


        <!-- GOOGLE MAPS LINK -->
        <a href="https://www.google.com/maps/search/{instance.address}"
           style="color:#0077cc;text-decoration:none;font-weight:bold;">
           View on Google Maps 🌍
        </a>

    </div>

    <!-- BUTTON -->
    <div style="text-align:center;margin-top:35px;">
      <a href="{publication_url}"
         style="background:#3fbbc0;color:white;padding:15px 35px;
                text-decoration:none;border-radius:30px;font-size:18px;
                font-weight:bold;display:inline-block;">
          💖 Support the Cause
      </a>
    </div>

    <!-- FOOTER -->
    <p style="margin-top:30px;font-size:14px;color:#777;text-align:center;">
        Interested in helping out? Visit <strong>Clinica+</strong> to donate or learn more.
    </p>

    <hr style="border:none;border-top:1px solid #eee;margin:30px 0;">

    <p style="font-size:13px;color:#777;text-align:center;">
        Kind regards,<br><br>
        <strong>Clinica+ Team</strong><br>
        General Coordination
    </p>

    </div>
    </div>
    """


    async_send(sujet, "", html_message, emails)
