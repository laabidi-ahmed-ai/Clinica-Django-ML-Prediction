# 🚀 Setup Guide for Recruiters

This guide will help you quickly set up and run the project to test all features.

## ⚡ Quick Start (5 minutes)

### Step 1: Install Dependencies
```bash
pip install django scikit-learn pandas numpy joblib stripe reportlab cloudinary
```

### Step 2: Get Free Test API Keys

#### Stripe Test Keys (Free - No Credit Card Required)
1. Go to: https://dashboard.stripe.com/test/apikeys
2. Sign up for a free account (or use test mode)
3. Get your test keys from the dashboard:
   - **Publishable Key:** Starts with `pk_test_...`
   - **Secret Key:** Starts with `sk_test_...`

#### Cloudinary (Free Tier Available)
1. Go to: https://cloudinary.com/users/register/free
2. Sign up for free account
3. Get your credentials from dashboard:
   - Cloud Name
   - API Key
   - API Secret

### Step 3: Configure Settings

Open `Clinica/settings.py` and replace the placeholders:

```python
# Line 16: Django Secret Key (generate your own)
SECRET_KEY = 'REPLACE_WITH_YOUR_SECRET_KEY'  # Generate: python -c "import secrets; print(secrets.token_urlsafe(50))"

# Lines 170-171: Stripe Keys (from Step 2)
STRIPE_PUBLISHABLE_KEY = "REPLACE_WITH_YOUR_STRIPE_PUBLISHABLE_KEY"
STRIPE_SECRET_KEY = "REPLACE_WITH_YOUR_STRIPE_SECRET_KEY"

# Lines 225-227: Cloudinary (from Step 2)
CLOUDINARY_STORAGE = {
    'CLOUD_NAME': 'REPLACE_WITH_YOUR_CLOUD_NAME',
    'API_KEY': 'REPLACE_WITH_YOUR_API_KEY',
    'API_SECRET': 'REPLACE_WITH_YOUR_API_SECRET',
}

# Lines 231-233: Cloudinary config
cloudinary.config(
    cloud_name="REPLACE_WITH_YOUR_CLOUD_NAME",
    api_key="REPLACE_WITH_YOUR_API_KEY",
    api_secret="REPLACE_WITH_YOUR_API_SECRET",
)
```

**Note:** Email and Telegram settings are optional - the core features work without them.

### Step 4: Run Migrations
```bash
python manage.py migrate
```

### Step 5: Create Superuser (Optional - for admin access)
```bash
python manage.py createsuperuser
```

### Step 6: Generate ML Training Data (Optional - for ML features)
```bash
# Generate historical data
python manage.py generate_historical_orders --days 90

# Train the ML model
python manage.py train_stock_model
```

### Step 7: Run the Server
```bash
python manage.py runserver
```

Visit: http://127.0.0.1:8000/

---

## 🎯 Testing Key Features

### 1. ML Stock Prediction
- Add a product via admin panel
- The system will automatically generate training data and train the model
- View predictions in the products list

### 2. E-Commerce Features
- Browse products at: `/`
- Add products to cart
- Test payment flow (uses Stripe test mode - no real charges)
- Complete checkout

### 3. Health Quiz
- Go to cart page
- Click "Take Health Quiz"
- Answer 3 questions
- Get coupon code if perfect score

### 4. Dynamic Search
- Type in the search bar on product page
- See autocomplete suggestions

### 5. PDF Export
- Go to admin dashboard
- Click "Export Orders PDF"
- Download comprehensive report

---

## 📝 Notes

- **Stripe Test Mode:** All payments are in test mode - use test card: `4242 4242 4242 4242`
- **Email:** Email notifications work if you configure SMTP, otherwise they'll fail silently (optional)
- **Cloudinary:** Required for image uploads. Free tier is sufficient for testing
- **Database:** Uses SQLite (included) - no setup needed

---

## 🐛 Troubleshooting

**Issue: "No module named 'stripe'"**
```bash
pip install stripe
```

**Issue: "ML model not training"**
- Make sure you have at least one product in the database
- Run: `python manage.py generate_historical_orders --days 90`

**Issue: "Stripe payment fails"**
- Make sure you're using test keys (start with `pk_test_` and `sk_test_`)
- Use test card number: `4242 4242 4242 4242`

**Issue: "Email not sending"**
- Email is optional for core features
- To test emails, configure Gmail App Password in settings

---

## ✅ What Works Without Configuration

- ✅ Product browsing
- ✅ Shopping cart
- ✅ ML stock predictions (with generated data)
- ✅ Dynamic search
- ✅ Health quiz
- ✅ Admin dashboard
- ✅ PDF export

## ⚙️ What Needs Configuration

- ⚙️ Stripe payments (need test keys - free)
- ⚙️ Image uploads (need Cloudinary - free tier available)
- ⚙️ Email notifications (optional)

---

**All features are fully functional once you add the free test API keys!**
