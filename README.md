# 🏥 Clinica+ — Intelligent Clinic Management Web Application

Clinica+ is a web application developed with Django that enables efficient, secure, and centralized management of all activities of a medical clinic.
This project follows the Agile Scrum methodology, with sprint-based organization and planning based on a complete product backlog.

## 🚀 Project Objective

Facilitate the daily management of a clinic by automating internal processes, improving communication between medical and administrative staff, and providing patients with digital tracking of their information and analyses.

---

## 📦 My Contribution: E-Commerce & Product Management Module

**Modules:** `achatapp` & `produits`  
**Key Feature:** **ML-Powered Stock Rupture Prediction System** 🧠

This module implements a complete e-commerce solution for medical products with advanced features including machine learning-based stock prediction, payment processing, and intelligent product management.

### 🎯 Key Highlights for Recruiters

- ✅ **End-to-End ML Pipeline:** Built complete ML system from data generation → model training → production deployment
- ✅ **Random Forest Model:** Implemented stock rupture prediction using scikit-learn with 6 engineered features
- ✅ **Production-Ready:** Integrated ML predictions into Django web application with error handling and fallbacks
- ✅ **Full-Stack Development:** Payment processing (Stripe), email notifications, PDF generation, real-time search
- ✅ **Cold Start Solution:** Solved data sparsity problem with intelligent synthetic data generation
- ✅ **Hybrid ML Approach:** Combined ML predictions with rule-based logic for reliability

## 🎬 Demo (YouTube)
 
👉 **[Your YouTube demo link]([YOUR_YOUTUBE_URL_HERE](https://youtu.be/2VLYOraU0jg?si=tvxAQtXO3HcGvEFp))**
---

## ✨ Key Functionalities

### 1. 🧠 **ML-Powered Stock Rupture Prediction System** (Advanced Feature)

The system uses **Random Forest Machine Learning** to predict when products will run out of stock, helping prevent inventory shortages.

#### How It Works:

**Step 1: Automatic Historical Data Generation**
- Since real historical sales data may not exist initially, the system automatically generates realistic historical order data
- Command: `python manage.py generate_historical_orders --days 90`
- The generator creates orders based on:
  - Product category (medical consumables, medicines, equipment)
  - Product price (expensive products = fewer sales, cheap products = more sales)
  - Realistic daily sales rates calculated from price and category
- Generates 90 days of historical data with varying quantities, dates, and customer information

**Step 2: Model Training**
- Command: `python manage.py train_stock_model`
- The system extracts features from historical data:
  - **Current stock** quantity
  - **Average daily sales** (calculated over 90 days)
  - **7-day trend** (recent sales pattern)
  - **Sales variance** (variability in weekly sales)
  - **Product category** (encoded for ML model)
  - **Selling price** (normalized)
- Creates training samples by simulating different stock scenarios (50, 100, 200, 500 units)
- Trains a **Random Forest Regressor** model with:
  - 100 decision trees
  - Maximum depth of 10
  - Train/test split (80/20)
  - Model saved as `stock_predictor.joblib`

**Model Evaluation:**
- **Train Score (R²):** Measures model performance on training data
- **Test Score (R²):** Measures generalization on unseen test data
- **Validation Strategy:** 80/20 train-test split with random state=42 for reproducibility
- **Performance Metrics:** R² score (coefficient of determination) logged after training
- **Edge Cases Handled:**
  - Minimum 10 samples required for training
  - Filters invalid predictions (days > 365 or < 0)
  - Handles missing features gracefully
  - Fallback to rule-based prediction if ML model unavailable

**Step 3: Prediction Algorithm**
The prediction uses a **hybrid approach** combining ML predictions with rule-based logic:

1. **Price-Based Daily Sales Estimation:**
   - Products > 1000 DT: 0.05 sales/day (very rare)
   - Products 500-1000 DT: 0.25 sales/day
   - Products 200-500 DT: 0.6 sales/day
   - Products 100-200 DT: 1.0 sales/day
   - Products 40-100 DT: 1.2 sales/day
   - Products 20-40 DT: 3.0 sales/day
   - Products 10-20 DT: 5.0 sales/day
   - Products < 10 DT: 8.0 sales/day (frequent)

2. **Historical Data Integration:**
   - If historical sales data exists, it's intelligently combined with price estimates
   - For expensive products (>200 DT): 80% price estimate, 20% historical data
   - For medium products (100-200 DT): 60% price estimate, 40% historical data
   - For cheap products (<10 DT): 20% price estimate, 80% historical data

3. **Quantity Multipliers:**
   - Stock ≥ 100 units: multiply days by 1.5x-2x
   - Stock ≥ 50 units: multiply days by 1.2x-1.5x
   - Minimum days calculated based on price × quantity

4. **Final Calculation:**
   ```
   days_until_out = (stock / final_daily_sales) × quantity_multiplier
   ```

**Step 4: Stock Status Classification**
- **Out of Stock:** quantity = 0
- **Low Stock:** ≤ 7 days remaining (red alert)
- **Medium Stock:** 8-30 days remaining (yellow warning)
- **Good Stock:** > 30 days remaining (green)

**Automatic Training:**
- When a new product is added, the system automatically:
  1. Generates 90 days of historical data in the background
  2. Trains the ML model
  3. Makes predictions immediately available

---

### 2. 🔍 **Dynamic Product Search (Autocomplete)**

Real-time product search with instant suggestions as users type.

**Features:**
- **API Endpoint:** `/api/product-suggestions/?q=search_term`
- **Case-insensitive** search matching product names
- **Live suggestions** appear in a dropdown as you type
- **Product preview** showing:
  - Product image
  - Name (with highlighted search term)
  - Category
  - Price
  - Stock status
- **Click to select** and automatically filter products
- **Debounced requests** to optimize performance

**Implementation:**
- JavaScript-based autocomplete with AJAX calls
- Returns top 10 matching products
- Visual highlighting of search terms
- Responsive design for mobile and desktop

---

### 3. 🎯 **Health Quiz with Coupon Generation**

Interactive health quiz that rewards users with discount coupons.

**How It Works:**
1. **Quiz Access:** Available from the shopping cart page
2. **Question Source:**
   - Primary: Fetches health-related questions from Open Trivia DB API
   - Fallback: High-quality local questions if API is unavailable
   - Questions cover: nutrition, exercise, sleep, vitamins, water intake, etc.
3. **Quiz Flow:**
   - 3 health-related questions
   - Multiple choice format
   - Real-time validation
4. **Reward System:**
   - **Perfect Score (3/3):** Generates unique 5% discount coupon
   - Coupon code format: `HEALTHXXXXXX` (6 random characters)
   - Coupon valid for 30 days
   - Single use per user
   - Automatically applied to cart
5. **User Feedback:**
   - Success popup with coupon code on perfect score
   - Failure popup showing score (e.g., "2/3 correct")
   - Error handling for API failures

**Technical Details:**
- Service pattern implementation (`HealthQuizService`)
- Caching for API responses (1 hour)
- Session management for quiz state
- Secure coupon generation with uniqueness validation

---

### 4. 💳 **Stripe Payment Integration**

Secure payment processing using Stripe Checkout.

**Features:**
- **Stripe Checkout Session** creation
- **Secure card payments** (PCI compliant)
- **Automatic price calculation** with coupon discounts
- **Proportional discount distribution** across cart items
- **Payment verification** before order creation
- **Success/Cancel URLs** for payment flow
- **Customer email** collection for receipts

**Payment Flow:**
1. User fills checkout form (name, email, phone, address)
2. Form validation (email format, phone format, etc.)
3. Stock verification before payment
4. Stripe Checkout Session created with line items
5. User redirected to Stripe payment page
6. After payment:
   - Payment verified via Stripe API
   - Orders created with `amount_paid` field
   - Stock automatically deducted
   - Cart cleared
   - Success page displayed

**Security:**
- All sensitive operations server-side
- Stripe secret key in environment variables
- Payment verification before order confirmation
- No card data stored locally

---

### 5. 📧 **Email Notifications for Order Acceptance**

Automated email system for order confirmations.

**Features:**
- **HTML email templates** with professional design
- **Order details** included:
  - Order ID
  - Product name and quantity
  - Total amount
  - Delivery address
- **Order tracking link** with secure token
- **Delivery information** (24-48 hours)
- **Branded design** with clinic colors
- **Plain text fallback** for email clients

**When Emails Are Sent:**
- Automatically when admin accepts an order
- Email sent to customer's provided email address
- Includes secure tracking URL: `/order/track/{order_id}/{token}/`

**Email Content:**
- Professional HTML template
- Order summary
- Delivery timeline
- Tracking link
- Contact information

---

### 6. 📄 **PDF Order Report Export**

Generate comprehensive PDF reports of all orders.

**Features:**
- **Export all orders** to PDF format
- **Landscape orientation** for better readability
- **Comprehensive table** including:
  - Order ID
  - Product name
  - Customer information
  - Quantity
  - Total amount
  - Status (Pending/Accepted/Rejected)
  - Date
  - Phone number
  - Delivery address
- **Color-coded status** indicators
- **Summary statistics:**
  - Total orders
  - Pending/Accepted/Rejected counts
  - Total revenue
- **Professional formatting:**
  - Header with generation date
  - Alternating row colors
  - Text wrapping for long addresses
  - Grid borders

**Usage:**
- Available from admin dashboard
- One-click export
- Filename: `orders_report_YYYYMMDD_HHMMSS.pdf`

---

### 7. 🔥 **"Last Items, Product in Demand" Banner (Data-Driven)**

Dynamic visual alert banner that appears on product cards when stock prediction shows low inventory, creating urgency and encouraging purchases.

**Features:**
- **Prediction-Driven Display:** Banner appears when stock prediction shows < 30 days until stock rupture
- **Eye-Catching Design:**
  - Red gradient background with fire icon (🔥)
  - Positioned at top-left of product image
  - Professional styling with shadow effects
  - Uppercase text: "LAST ITEMS, PRODUCT IN DEMAND"
- **Real-Time Updates:** Banner appears/disappears based on current stock predictions (calculated from stock quantity and historical sales data)
- **User Experience:**
  - Creates purchase urgency
  - Highlights high-demand products
  - Visual indicator of scarcity
  - Non-intrusive (doesn't block product image)

**How It Works:**
- Uses `get_stock_status()` method which calculates days until stock rupture
- Calculation based on:
  - Current stock quantity
  - Historical sales data (accepted orders from last 90 days)
  - Product price (for sales rate estimation)
- Formula: `days_until_out = (current_stock / daily_sales_rate) × multiplier`
- Threshold: < 30 days until stock rupture triggers the banner
- Automatically updates as stock and sales data change
- Works with hybrid prediction approach (price-based + historical orders)

**Business Impact:**
- **Increases Sales:** Creates urgency, encourages faster purchasing decisions
- **Inventory Management:** Helps clear low stock items before they expire
- **Customer Experience:** Transparent communication about product availability
- **Data-Driven:** Based on actual stock calculations using historical sales data, not arbitrary thresholds

---

### 8. ⚠️ **Low Stock Alert Popup Notifications (Admin Dashboard)**

Intelligent popup alerts for products running low on stock in the admin dashboard.

**Features:**
- **Automatic detection** of low stock products (quantity < 10)
- **Popup notification** on dashboard load
- **Visual indicators:**
  - Red alert for out of stock (0 units)
  - Orange alert for critical stock (≤ 3 units)
  - Yellow alert for low stock (4-9 units)
- **Product list** showing:
  - Product name
  - Current quantity
  - Days until out of stock (from ML prediction)
  - Stock status badge
- **Dismissible popup** with close button
- **Overlay background** for focus

**When It Appears:**
- Automatically on admin dashboard load
- Only if products with quantity < 10 exist
- Can be manually closed
- Reappears on page refresh if still applicable

**Integration with ML:**
- Shows predicted days until out of stock
- Color-coded based on ML predictions:
  - Red: ≤ 7 days
  - Yellow: 8-30 days
  - Green: > 30 days

---

## 🛠️ Technical Implementation

### Technologies Used:
- **Backend:** Django (Python)
- **Machine Learning:** scikit-learn (Random Forest)
- **Payment:** Stripe API
- **PDF Generation:** ReportLab
- **Email:** Django EmailMultiAlternatives
- **Frontend:** HTML, CSS, JavaScript, Bootstrap
- **Database:** SQLite

### Key Files:
- `achatapp/models.py` - Product and Order models with ML integration
- `achatapp/views.py` - All view functions (search, cart, payment, etc.)
- `achatapp/ml/stock_predictor.py` - ML model implementation
- `achatapp/management/commands/generate_historical_orders.py` - Data generation
- `achatapp/management/commands/train_stock_model.py` - Model training
- `achatapp/health_quiz_service.py` - Quiz service with API integration

### ML Model Details:
- **Algorithm:** Random Forest Regressor
- **Features:** 6 (stock, sales, trend, variance, category, price)
- **Training:** Automatic on product addition
- **Storage:** Joblib format (`stock_predictor.joblib`)
- **Fallback:** Rule-based prediction if ML unavailable

---

## 🚀 Setup & Usage

### Prerequisites:
```bash
pip install django scikit-learn pandas numpy joblib stripe reportlab
```

### ML Model Training:
```bash
# Generate historical data (90 days)
python manage.py generate_historical_orders --days 90

# Train the ML model
python manage.py train_stock_model
```

### Environment Variables:
```env
STRIPE_SECRET_KEY=your_stripe_secret_key
STRIPE_PUBLISHABLE_KEY=your_stripe_publishable_key
```

### 📖 For Recruiters:
**See [SETUP_FOR_RECRUITERS.md](SETUP_FOR_RECRUITERS.md) for complete setup instructions with free API keys.**

---

## 📊 Features Summary

| Feature | Description | Status |
|---------|-------------|--------|
| **ML Stock Prediction** | Random Forest model predicting stock rupture | ✅ Active |
| **Dynamic Search** | Real-time autocomplete product search | ✅ Active |
| **Health Quiz** | Interactive quiz with coupon rewards | ✅ Active |
| **Stripe Payment** | Secure payment processing | ✅ Active |
| **Email Notifications** | Order confirmation emails | ✅ Active |
| **PDF Export** | Comprehensive order reports | ✅ Active |
| **Low Stock Alerts** | Popup notifications for inventory | ✅ Active |
| **"Last Items" Banner** | Data-driven demand indicator based on stock predictions | ✅ Active |

---

## 🎯 Project Methodology

- **Methodology:** Agile Scrum
- **Tools:** GitHub, Visual Paradigm
- **Team:** Group project with individual module contributions

---

*This module represents a complete e-commerce solution with advanced ML capabilities for intelligent inventory management.*
