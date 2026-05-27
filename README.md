# 🏪 Store Debt Tracker (Utang Tracker)

A mobile-first Django web app for small store owners (sari-sari stores) to track customer debts and payments.

---

## 📱 Features

- **Dashboard** — Total unpaid debt, customer count, recent activity, top debtors
- **Customer Management** — Add, edit, delete, search customers
- **Debt Tracking (Utang)** — Record debts per customer with notes and date
- **Payment Tracking (Bayad)** — Record payments, auto-deducts from balance
- **Reports** — Customers ranked by debt, 30-day activity summary
- **CSV Export** — Export full report for spreadsheet use
- **High Debt Alerts** — Highlights customers owing ₱500+
- **Date Filtering** — Filter transactions by date range per customer
- **Bottom Navigation** — Mobile-friendly nav bar

---

## 🚀 Quick Setup

### 1. Install Python and Django

```bash
pip install django>=4.2
```

### 2. Navigate to project folder

```bash
cd store_debt_tracker
```

### 3. Run database migrations

```bash
python manage.py migrate
```

### 4. (Optional) Create admin user

```bash
python manage.py createsuperuser
```

### 5. Start the server

```bash
python manage.py runserver
```

### 6. Open in your browser or phone

```
http://127.0.0.1:8000/
```

To access from your phone on the same WiFi:
```
http://<your-computer-ip>:8000/
```

Run with: `python manage.py runserver 0.0.0.0:8000`

---

## 📁 Project Structure

```
store_debt_tracker/
├── config/
│   ├── settings.py       # Django settings
│   └── urls.py           # Root URL config
├── tracker/
│   ├── migrations/       # DB migrations
│   ├── templates/tracker/
│   │   ├── base.html          # Base layout + bottom nav
│   │   ├── dashboard.html     # Home screen
│   │   ├── customer_list.html # Customer list + search
│   │   ├── customer_detail.html  # Customer profile + history
│   │   ├── customer_form.html    # Add/edit customer
│   │   ├── debt_form.html        # Add debt (utang)
│   │   ├── payment_form.html     # Record payment (bayad)
│   │   └── reports.html          # Reports page
│   ├── models.py         # Customer, Debt, Payment
│   ├── views.py          # All views
│   ├── forms.py          # Django forms
│   └── urls.py           # App URLs
├── manage.py
├── requirements.txt
└── README.md
```

---

## 🎨 Design System

| Token       | Color     | Use               |
|-------------|-----------|-------------------|
| Background  | `#F8FAFC` | Page background   |
| Primary     | `#7DA7D9` | Buttons, active   |
| Secondary   | `#6FA3A3` | Payment actions   |
| Accent      | `#94A3B8` | Borders, muted    |
| Text        | `#1E293B` | Body text         |
| Danger      | `#E57373` | High debt, delete |
| Success     | `#66BB6A` | Payments, paid    |

---

## 📊 Database Models

### Customer
- `name` (CharField)
- `phone` (optional)
- `notes` (optional)
- `created_at`

### Debt
- `customer` (FK → Customer)
- `amount` (Decimal)
- `note` (optional)
- `date`

### Payment
- `customer` (FK → Customer)
- `amount` (Decimal)
- `note` (optional)
- `date`

**Balance** = Sum of all debts − Sum of all payments (computed, not stored)

---

## ⚠️ High Debt Threshold

Customers with a balance ≥ ₱500 are flagged as "High Debt" with a red badge.
You can change this in `tracker/models.py` → `is_high_debt()`.

---

## 🔒 Production Notes

Before deploying:
1. Change `SECRET_KEY` in `config/settings.py`
2. Set `DEBUG = False`
3. Set `ALLOWED_HOSTS` to your domain
4. Run `python manage.py collectstatic`
