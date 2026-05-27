from django.urls import path
from . import views

urlpatterns = [
    # Auth
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
    path('delete-account/', views.delete_account, name='delete_account'),

    # Password Recovery
    path('recover/', views.recovery_step1, name='recovery_step1'),
    path('recover/questions/', views.recovery_step2, name='recovery_step2'),
    path('recover/reset/', views.recovery_step3, name='recovery_step3'),

    # Dashboard
    path('', views.dashboard, name='dashboard'),

    # Customers
    path('customers/', views.customer_list, name='customer_list'),
    path('customers/autocomplete/', views.customer_autocomplete, name='customer_autocomplete'),
    path('customers/check-duplicate/', views.customer_check_duplicate, name='customer_check_duplicate'),
    path('customers/<int:pk>/', views.customer_detail, name='customer_detail'),
    path('customers/<int:pk>/edit/', views.customer_edit, name='customer_edit'),
    path('customers/<int:pk>/delete/', views.customer_delete, name='customer_delete'),

    # Transactions
    path('transactions/', views.transaction_list, name='transaction_list'),
    path('transactions/new/', views.transaction_create, name='transaction_create'),
    path('transactions/<int:pk>/', views.transaction_detail, name='transaction_detail'),
    path('transactions/<int:pk>/delete/', views.transaction_delete, name='transaction_delete'),

    # Payments
    path('transactions/<int:txn_pk>/pay/', views.payment_add, name='payment_add'),
    path('transactions/<int:txn_pk>/mark-paid/', views.mark_paid, name='mark_paid'),
    path('payments/<int:pk>/delete/', views.payment_delete, name='payment_delete'),

    path('transactions/<int:pk>/promise/', views.update_promise, name='update_promise'),

    # New transaction for existing customer
    path('customers/<int:customer_pk>/new-transaction/', views.new_transaction_for_customer, name='new_transaction_for_customer'),

    # Public Receipt (no login)
    path('receipt/<str:token>/', views.transaction_receipt, name='transaction_receipt'),

    # Reports & Export
    path('reports/', views.reports, name='reports'),
    path('export/', views.export_csv, name='export_csv'),
]
