"""
Django settings for Clinica project.
"""

from pathlib import Path
import ssl
import cloudinary
import cloudinary.uploader

BASE_DIR = Path(__file__).resolve().parent.parent

# ===========================
# GENERAL CONFIG
# ===========================

SECRET_KEY = 'REPLACE_WITH_YOUR_SECRET_KEY'  # Generate: python -c "import secrets; print(secrets.token_urlsafe(50))"
DEBUG = True

ALLOWED_HOSTS = [
    "127.0.0.1",
    "localhost",
    "*.ngrok-free.dev",
    "*"
]

# ===========================
# INSTALLED APPS
# ===========================

INSTALLED_APPS = [
    'UserApp',
    'Publication.apps.PublicationConfig',
    'Donation',
    'achatapp',
    'Labapp',
    'gestionPatient',
    'stages',
    'stagiaire',
    'channels',


    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Cloudinary
    'django.contrib.sites',
    'cloudinary',
    'cloudinary_storage',
    'todo_app',
]
ASGI_APPLICATION = "Clinica.asgi.application"

# Optional: simple in-memory channel layer
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels.layers.InMemoryChannelLayer"
    },
}


SITE_ID = 1

# ===========================
# MIDDLEWARE
# ===========================

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'Clinica.urls'

# ===========================
# TEMPLATES
# ===========================

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'Templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'Clinica.wsgi.application'

# ===========================
# DATABASE
# ===========================

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# ===========================
# PASSWORD VALIDATION
# ===========================

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# ===========================
# LANGUAGE & TIMEZONE
# ===========================

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# ===========================
# STATIC & MEDIA
# ===========================

STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# ===========================
# USER MODEL
# ===========================

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
AUTH_USER_MODEL = 'UserApp.User'

LOGIN_REDIRECT_URL = 'front_index'
LOGIN_URL = 'loginFront'
LOGOUT_REDIRECT_URL = 'loginFront'

AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
]

# ===========================
# STRIPE MULTI-KEY CONFIG
# ===========================

# Payment for PRODUCTS
#STRIPE_PRODUCT_PUBLISHABLE = "pk_test_51SYXvkAur5Kid2sRq0dvSwd99hMVqv6WKHEDjqUJhxOL8fRwL2coCeBa0qRhP8iSJV6iR5b56j7Tgg9L7JOiTMG500OsUo8Gtk"
#STRIPE_PRODUCT_SECRET = "sk_test_51SYXvkAur5Kid2sRMLGjmqJtizIK73XlIY75brqzE8zSFH23lSUDYdwDvIt9HzPxJoBtWg4jQslwDl2qpHPnv4xj00Cefy7BrN"

# Payment for DONATIONS
STRIPE_PUBLISHABLE_KEY = "REPLACE_WITH_YOUR_STRIPE_PUBLISHABLE_KEY"  # Get from: https://dashboard.stripe.com/test/apikeys
STRIPE_SECRET_KEY = "REPLACE_WITH_YOUR_STRIPE_SECRET_KEY"  # Get from: https://dashboard.stripe.com/test/apikeys

# ===========================
# EMAIL MULTI-ACCOUNT CONFIG
# ===========================


#email
# tout en bas de settings.py
# ===========================
# FIX SSL Gmail + Python 3.12/3.13 on Windows
# ===========================



# ===========================
# CONFIGURATION EMAIL GMAIL
# ===========================
# Email Gmail via SSL — FONCTIONNE SUR PYTHON 3.13 / WINDOWS
# ========= CONFIG EMAIL GMAIL (python 3.13 compatible) ==========
# ==========================
# EMAIL - GMAIL (PYTHON 3.13)
# ==========================


# ============================
# FIX PYTHON 3.13 + SSL GMAIL
# ============================
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"

EMAIL_HOST = "smtp.gmail.com"
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_USE_SSL = False

EMAIL_HOST_USER = "REPLACE_WITH_YOUR_EMAIL@gmail.com"  # Optional - for email notifications
EMAIL_HOST_PASSWORD = "REPLACE_WITH_YOUR_APP_PASSWORD"  # Gmail App Password (optional)

DEFAULT_FROM_EMAIL = "Clinica+ Team <mejri.cyrine.s2@gmail.com>"

# NO SSL PATCH. NOTHING SPECIAL.
# NO import ssl, NO certifi, NO monkey patch.


# Gmail fix Python 3.13 (required)
ssl._create_default_https_context = ssl._create_unverified_context

# ===========================
# CLOUDINARY
# ===========================

DEFAULT_FILE_STORAGE = 'cloudinary_storage.storage.MediaCloudinaryStorage'

CLOUDINARY_STORAGE = {
    'CLOUD_NAME': 'REPLACE_WITH_YOUR_CLOUD_NAME',  # Get from: https://cloudinary.com
    'API_KEY': 'REPLACE_WITH_YOUR_API_KEY',
    'API_SECRET': 'REPLACE_WITH_YOUR_API_SECRET',
}

cloudinary.config(
    cloud_name="REPLACE_WITH_YOUR_CLOUD_NAME",
    api_key="REPLACE_WITH_YOUR_API_KEY",
    api_secret="REPLACE_WITH_YOUR_API_SECRET",
)

# ===========================
# TELEGRAM BOT
# ===========================

TELEGRAM_BOT_TOKEN = "REPLACE_WITH_YOUR_TELEGRAM_BOT_TOKEN"  # Optional - for Telegram features
TELEGRAM_BOT_USERNAME = "ClinicaPlusN_bot"
TELEGRAM_WEBHOOK_SECRET = "clinica_telegram_42198"

# ===========================
# QR CODE EMAIL DOMAIN
# ===========================

SITE_DOMAIN = "192.168.56.1"
SITE_PORT = "8000"
USE_HTTPS = False

#=================================
#Service mail
#==================================
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'         
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'REPLACE_WITH_YOUR_EMAIL@gmail.com'  # Optional
EMAIL_HOST_PASSWORD = 'REPLACE_WITH_YOUR_APP_PASSWORD'  # Optional
