import csv
import json
from datetime import date, datetime
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Q, Sum
from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_POST

from .models import Customer, Transaction, TransactionItem, TransactionPayment, UserSecurityProfile
from .forms import (RegisterForm, LoginForm, CustomerForm,
                    TransactionForm, TransactionItemForm, TransactionPaymentForm,
                    RecoveryStep1Form, RecoveryStep2Form, RecoveryStep3Form)


# ─── Auth ────────────────────────────────────────────────────────────────────

def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            login(request, form.get_user())
            return redirect('dashboard')
    else:
        form = LoginForm(request)
    return render(request, 'tracker/auth/login.html', {'form': form})


def register_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Save security profile
            cd = form.cleaned_data
            UserSecurityProfile.objects.create(
                user=user,
                question_1=cd['question_1'],
                custom_question_1=cd.get('custom_question_1', '') or None,
                answer_1_hash=UserSecurityProfile.hash_answer(cd['answer_1']),
                question_2=cd['question_2'],
                custom_question_2=cd.get('custom_question_2', '') or None,
                answer_2_hash=UserSecurityProfile.hash_answer(cd['answer_2']),
            )
            login(request, user)
            messages.success(request, f'Welcome, {user.username}! Your store account is ready.')
            return redirect('dashboard')
    else:
        form = RegisterForm()
    return render(request, 'tracker/auth/register.html', {'form': form})


@login_required
def logout_view(request):
    logout(request)
    return render(request, 'tracker/auth/logout.html')


# ─── Password Recovery (3-step) ───────────────────────────────────────────────

def recovery_step1(request):
    """Step 1 — enter username."""
    if request.user.is_authenticated:
        return redirect('dashboard')
    form = RecoveryStep1Form(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        username = form.cleaned_data['username']
        request.session['recovery_username'] = username
        request.session['recovery_verified'] = False
        return redirect('recovery_step2')
    return render(request, 'tracker/auth/recovery_step1.html', {'form': form})


def recovery_step2(request):
    """Step 2 — answer security questions."""
    if request.user.is_authenticated:
        return redirect('dashboard')
    username = request.session.get('recovery_username')
    if not username:
        return redirect('recovery_step1')
    try:
        user = User.objects.get(username=username)
        profile = user.security_profile
    except (User.DoesNotExist, UserSecurityProfile.DoesNotExist):
        return redirect('recovery_step1')

    form = RecoveryStep2Form(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        a1 = form.cleaned_data['answer_1']
        a2 = form.cleaned_data['answer_2']
        if profile.check_answer_1(a1) and profile.check_answer_2(a2):
            request.session['recovery_verified'] = True
            return redirect('recovery_step3')
        else:
            form.add_error(None, 'One or both answers are incorrect. Please try again.')

    return render(request, 'tracker/auth/recovery_step2.html', {
        'form': form,
        'question_1': profile.get_question_1_text(),
        'question_2': profile.get_question_2_text(),
        'username': username,
    })


def recovery_step3(request):
    """Step 3 — set new password."""
    if request.user.is_authenticated:
        return redirect('dashboard')
    username = request.session.get('recovery_username')
    verified = request.session.get('recovery_verified', False)
    if not username or not verified:
        return redirect('recovery_step1')
    try:
        user = User.objects.get(username=username)
    except User.DoesNotExist:
        return redirect('recovery_step1')

    form = RecoveryStep3Form(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user.set_password(form.cleaned_data['new_password1'])
        user.save()
        # Clear recovery session
        request.session.pop('recovery_username', None)
        request.session.pop('recovery_verified', None)
        messages.success(request, 'Password reset successfully! Please sign in.')
        return redirect('login')

    return render(request, 'tracker/auth/recovery_step3.html', {
        'form': form,
        'username': username,
    })


@login_required
def delete_account(request):
    if request.method == 'POST':
        user = request.user
        logout(request)
        user.delete()
        messages.success(request, 'Your account has been deleted.')
        return redirect('login')
    return render(request, 'tracker/auth/delete_account.html')


# ─── Dashboard ───────────────────────────────────────────────────────────────

@login_required
def dashboard(request):
    customers = Customer.objects.filter(owner=request.user)
    customer_count = customers.count()

    all_customers = list(customers)
    total_debt = sum(c.total_balance() for c in all_customers)

    # Recent transactions
    recent_txns = Transaction.objects.filter(
        customer__owner=request.user
    ).select_related('customer').prefetch_related('items', 'payments')[:8]

    # Top debtors
    top_debtors = sorted(all_customers, key=lambda c: c.total_balance(), reverse=True)
    top_debtors = [c for c in top_debtors if c.total_balance() > 0][:5]

    unpaid_count = Transaction.objects.filter(
        customer__owner=request.user, status__in=['unpaid', 'partial']
    ).count()

    # Promise-to-pay monitor — unpaid/partial transactions that have a promise date
    today = date.today()
    promise_txns_qs = Transaction.objects.filter(
        customer__owner=request.user,
        status__in=['unpaid', 'partial'],
        promise_date__isnull=False,
    ).select_related('customer').prefetch_related('items', 'payments').order_by('promise_date')

    promise_items = []
    for txn in promise_txns_qs:
        delta = (txn.promise_date - today).days
        if delta < 0:
            status_label = 'Overdue'
            status_cls   = 'promise-overdue'
        elif delta == 0:
            status_label = 'Due Today'
            status_cls   = 'promise-today'
        elif delta <= 3:
            status_label = f'In {delta} day{"s" if delta != 1 else ""}'
            status_cls   = 'promise-soon'
        else:
            status_label = f'In {delta} days'
            status_cls   = 'promise-upcoming'
        promise_items.append({
            'txn': txn,
            'delta': delta,
            'status_label': status_label,
            'status_cls': status_cls,
        })

    overdue_count = sum(1 for p in promise_items if p['status_cls'] == 'promise-overdue')
    due_today_count = sum(1 for p in promise_items if p['status_cls'] == 'promise-today')

    context = {
        'total_debt': total_debt,
        'customer_count': customer_count,
        'recent_txns': recent_txns,
        'top_debtors': top_debtors,
        'unpaid_count': unpaid_count,
        'promise_items': promise_items,
        'overdue_count': overdue_count,
        'due_today_count': due_today_count,
        'active_nav': 'dashboard',
    }
    return render(request, 'tracker/dashboard.html', context)


# ─── Customers ───────────────────────────────────────────────────────────────

@login_required
def customer_list(request):
    query = request.GET.get('q', '').strip()
    customers = Customer.objects.filter(owner=request.user)
    if query:
        customers = customers.filter(Q(name__icontains=query) | Q(phone__icontains=query))

    customer_data = []
    for c in customers:
        customer_data.append({
            'customer': c,
            'balance': c.total_balance(),
            'is_high': c.is_high_debt(),
        })
    customer_data.sort(key=lambda x: x['balance'], reverse=True)

    return render(request, 'tracker/customer_list.html', {
        'customer_data': customer_data,
        'query': query,
        'active_nav': 'customers',
    })


@login_required
def customer_detail(request, pk):
    customer = get_object_or_404(Customer, pk=pk, owner=request.user)
    transactions = customer.transactions.prefetch_related('items', 'payments').all()

    # Date filter
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    status_filter = request.GET.get('status', '')

    if date_from:
        transactions = transactions.filter(date__gte=date_from)
    if date_to:
        transactions = transactions.filter(date__lte=date_to)
    if status_filter:
        transactions = transactions.filter(status=status_filter)

    context = {
        'customer': customer,
        'transactions': transactions,
        'balance': customer.total_balance(),
        'total_charged': customer.total_charged(),
        'total_paid': customer.total_paid(),
        'is_high': customer.is_high_debt(),
        'date_from': date_from,
        'date_to': date_to,
        'status_filter': status_filter,
        'active_nav': 'customers',
    }
    return render(request, 'tracker/customer_detail.html', context)


@login_required
def customer_edit(request, pk):
    customer = get_object_or_404(Customer, pk=pk, owner=request.user)
    if request.method == 'POST':
        form = CustomerForm(request.POST, instance=customer)
        if form.is_valid():
            form.save()
            messages.success(request, 'Customer updated.')
            return redirect('customer_detail', pk=pk)
    else:
        form = CustomerForm(instance=customer)
    return render(request, 'tracker/customer_form.html', {
        'form': form, 'customer': customer, 'active_nav': 'customers'
    })


@login_required
def customer_delete(request, pk):
    customer = get_object_or_404(Customer, pk=pk, owner=request.user)
    if request.method == 'POST':
        name = customer.name
        customer.delete()
        messages.success(request, f'"{name}" deleted.')
        return redirect('customer_list')
    return render(request, 'tracker/customer_confirm_delete.html', {
        'customer': customer, 'active_nav': 'customers'
    })


# ─── Transactions ─────────────────────────────────────────────────────────────

@login_required
def transaction_create(request):
    """Create a new transaction. Customer name typed inline → auto-create if new."""
    if request.method == 'POST':
        customer_name = request.POST.get('customer_name', '').strip()
        customer_phone = request.POST.get('customer_phone', '').strip()
        txn_date = request.POST.get('date') or date.today()
        txn_time = request.POST.get('time') or datetime.now().strftime('%H:%M')
        txn_notes = request.POST.get('notes', '').strip()
        txn_promise_date = request.POST.get('promise_date') or None
        txn_promise_time = request.POST.get('promise_time') or None

        # Item arrays
        item_names = request.POST.getlist('item_name')
        item_units = request.POST.getlist('unit')
        quantities = request.POST.getlist('quantity')
        prices = request.POST.getlist('price')

        errors = []
        if not customer_name:
            errors.append('Customer name is required.')

        valid_items = []
        for i, (n, u, q, p) in enumerate(zip(item_names, item_units, quantities, prices)):
            n = n.strip()
            if not n and not u and not q and not p:
                continue  # skip blank rows
            if not n:
                errors.append(f'Row {i+1}: Item name is required.')
                continue
            u = u.strip().lower() if u else 'qty'
            if u not in ['kg', 'qty']:
                errors.append(f'Row {i+1}: Unit must be kg or qty.')
                continue
            try:
                q = float(q) if q else 1
                p = float(p) if p else 0
                if q <= 0:
                    errors.append(f'Row {i+1}: Quantity must be positive.')
                    continue
                valid_items.append((n, u, q, p))
            except ValueError:
                errors.append(f'Row {i+1}: Invalid quantity or price.')

        if not valid_items:
            errors.append('Add at least one item.')

        if errors:
            for e in errors:
                messages.error(request, e)
            return render(request, 'tracker/transaction_form.html', {
                'post': request.POST,
                'active_nav': 'transactions',
            })

        # Get or create customer
        customer, created = Customer.objects.get_or_create(
            owner=request.user,
            name__iexact=customer_name,
            defaults={'name': customer_name, 'phone': customer_phone or None}
        )
        if not created and customer_phone and not customer.phone:
            customer.phone = customer_phone
            customer.save()

        txn = Transaction.objects.create(
            customer=customer,
            date=txn_date,
            time=txn_time,
            notes=txn_notes or None,
            promise_date=txn_promise_date,
            promise_time=txn_promise_time,
            status='unpaid',
        )
        for n, u, q, p in valid_items:
            TransactionItem.objects.create(
                transaction=txn,
                item_name=n,
                unit=u,
                quantity=q,
                price=p,
            )

        messages.success(request, f'Transaction created for {customer.name}!')
        return redirect('transaction_detail', pk=txn.pk)

    prefill_name = request.session.pop('prefill_customer_name', '')
    prefill_phone = request.session.pop('prefill_customer_phone', '')
    existing_customers = list(
        Customer.objects.filter(owner=request.user).values('id', 'name', 'phone').order_by('name')
    )
    return render(request, 'tracker/transaction_form.html', {
        'today': date.today().isoformat(),
        'active_nav': 'transactions',
        'prefill_customer_name': prefill_name,
        'prefill_customer_phone': prefill_phone,
        'existing_customers': existing_customers,
    })


@login_required
def transaction_detail(request, pk):
    txn = get_object_or_404(Transaction, pk=pk, customer__owner=request.user)
    from datetime import datetime as dt
    payment_form = TransactionPaymentForm(initial={'date': date.today(), 'paid_time': dt.now().strftime('%H:%M')})
    return render(request, 'tracker/transaction_detail.html', {
        'txn': txn,
        'items': txn.items.all(),
        'payments': txn.payments.all(),
        'payment_form': payment_form,
        'active_nav': 'transactions',
    })


@login_required
def transaction_delete(request, pk):
    txn = get_object_or_404(Transaction, pk=pk, customer__owner=request.user)
    customer_pk = txn.customer.pk
    if request.method == 'POST':
        txn.delete()
        messages.success(request, 'Transaction deleted.')
        return redirect('customer_detail', pk=customer_pk)
    return render(request, 'tracker/transaction_confirm_delete.html', {
        'txn': txn, 'active_nav': 'transactions'
    })


@login_required
def transaction_list(request):
    query = request.GET.get('q', '').strip()
    status = request.GET.get('status', '')
    txns = Transaction.objects.filter(
        customer__owner=request.user
    ).select_related('customer').prefetch_related('items', 'payments')

    if query:
        txns = txns.filter(customer__name__icontains=query)
    if status:
        txns = txns.filter(status=status)

    return render(request, 'tracker/transaction_list.html', {
        'txns': txns,
        'query': query,
        'status': status,
        'active_nav': 'transactions',
    })


# ─── Payments ─────────────────────────────────────────────────────────────────

@login_required
def payment_add(request, txn_pk):
    txn = get_object_or_404(Transaction, pk=txn_pk, customer__owner=request.user)
    if request.method == 'POST':
        form = TransactionPaymentForm(request.POST)
        if form.is_valid():
            payment = form.save(commit=False)
            payment.transaction = txn
            payment.save()
            txn.update_status()
            messages.success(request, f'Payment of ₱{payment.amount} recorded.')
            return redirect('transaction_detail', pk=txn.pk)
    else:
        from datetime import datetime as dt
        form = TransactionPaymentForm(initial={'date': date.today(), 'paid_time': dt.now().strftime('%H:%M')})
    return render(request, 'tracker/transaction_detail.html', {
        'txn': txn,
        'items': txn.items.all(),
        'payments': txn.payments.all(),
        'payment_form': form,
        'active_nav': 'transactions',
    })


@login_required
def payment_delete(request, pk):
    payment = get_object_or_404(TransactionPayment, pk=pk, transaction__customer__owner=request.user)
    txn = payment.transaction
    if request.method == 'POST':
        payment.delete()
        txn.update_status()
        messages.success(request, 'Payment deleted.')
        return redirect('transaction_detail', pk=txn.pk)
    return render(request, 'tracker/payment_confirm_delete.html', {
        'payment': payment, 'active_nav': 'transactions'
    })


@login_required
@require_POST
def mark_paid(request, txn_pk):
    """Mark a transaction as fully paid by recording the remaining balance as a payment."""
    txn = get_object_or_404(Transaction, pk=txn_pk, customer__owner=request.user)
    remaining = txn.remaining_balance()
    if remaining > 0:
        TransactionPayment.objects.create(
            transaction=txn,
            amount=remaining,
            date=date.today(),
            note='Marked as fully paid',
        )
        txn.update_status()
        messages.success(request, f'Transaction marked as fully paid. ₱{remaining:.2f} recorded.')
    else:
        messages.info(request, 'Transaction is already fully paid.')
    return redirect('transaction_detail', pk=txn.pk)


@login_required
@require_POST
def update_promise(request, pk):
    """Update the promise-to-pay date/time on a transaction."""
    txn = get_object_or_404(Transaction, pk=pk, customer__owner=request.user)
    txn.promise_date = request.POST.get('promise_date') or None
    txn.promise_time = request.POST.get('promise_time') or None
    txn.save(update_fields=['promise_date', 'promise_time'])
    messages.success(request, 'Promise date updated.')
    return redirect('transaction_detail', pk=txn.pk)


@login_required
def new_transaction_for_customer(request, customer_pk):
    """Redirect to the new transaction form pre-filled with a customer's name."""
    customer = get_object_or_404(Customer, pk=customer_pk, owner=request.user)
    # Pass customer info via session so the form can pre-fill it
    request.session['prefill_customer_name'] = customer.name
    request.session['prefill_customer_phone'] = customer.phone or ''
    return redirect('transaction_create')


# ─── Reports ─────────────────────────────────────────────────────────────────

@login_required
def reports(request):
    customers = list(Customer.objects.filter(owner=request.user))
    customers_by_debt = sorted(customers, key=lambda c: c.total_balance(), reverse=True)
    customers_with_debt = [c for c in customers_by_debt if c.total_balance() > 0]

    total_outstanding = sum(c.total_balance() for c in customers)
    total_unpaid_txns = Transaction.objects.filter(
        customer__owner=request.user, status='unpaid'
    ).count()
    total_partial_txns = Transaction.objects.filter(
        customer__owner=request.user, status='partial'
    ).count()

    recent_txns = Transaction.objects.filter(
        customer__owner=request.user
    ).select_related('customer').prefetch_related('items', 'payments').order_by('-created_at')[:10]

    context = {
        'customers_with_debt': customers_with_debt,
        'total_outstanding': total_outstanding,
        'total_unpaid_txns': total_unpaid_txns,
        'total_partial_txns': total_partial_txns,
        'recent_txns': recent_txns,
        'active_nav': 'reports',
    }
    return render(request, 'tracker/reports.html', context)


# ─── Export ──────────────────────────────────────────────────────────────────

@login_required
def export_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="store_report.csv"'
    writer = csv.writer(response)

    writer.writerow(['=== CUSTOMER SUMMARY ==='])
    writer.writerow(['Name', 'Phone', 'Total Charged', 'Total Paid', 'Balance', 'Status'])
    for c in Customer.objects.filter(owner=request.user).order_by('name'):
        balance = c.total_balance()
        status = 'High Debt' if c.is_high_debt() else ('Has Debt' if balance > 0 else 'Settled')
        writer.writerow([c.name, c.phone or '', f'{c.total_charged():.2f}',
                         f'{c.total_paid():.2f}', f'{balance:.2f}', status])

    writer.writerow([])
    writer.writerow(['=== TRANSACTION DETAILS ==='])
    writer.writerow(['Customer', 'Date', 'Items', 'Total', 'Paid', 'Balance', 'Status', 'Notes'])
    txns = Transaction.objects.filter(customer__owner=request.user).select_related('customer').prefetch_related('items', 'payments')
    for txn in txns:
        items_str = '; '.join(f"{i.item_name}x{i.quantity}@{i.price}" for i in txn.items.all())
        writer.writerow([
            txn.customer.name, txn.date, items_str,
            f'{txn.total_amount():.2f}', f'{txn.total_paid():.2f}',
            f'{txn.remaining_balance():.2f}', txn.get_status_display(),
            txn.notes or ''
        ])
    return response


# ─── Customer name autocomplete (search2 — fast ranked lookup) ───────────────

@login_required
def customer_autocomplete(request):
    """
    search2: ranked, multi-strategy fast lookup.
    Priority 1 – starts-with match (most relevant, shown first)
    Priority 2 – contains match (broader fallback)
    Deduped, capped at 10 results.
    """
    q = request.GET.get('q', '').strip()
    if not q:
        # Return top customers (recently active) when query is empty
        customers = (
            Customer.objects.filter(owner=request.user)
            .order_by('name')
            .values('id', 'name', 'phone')[:10]
        )
        return JsonResponse({'results': list(customers)})

    base_qs = Customer.objects.filter(owner=request.user)

    # Tier 1: name starts with query (highest relevance)
    starts_with = list(
        base_qs.filter(name__istartswith=q)
        .values('id', 'name', 'phone')
        .order_by('name')[:10]
    )

    # Tier 2: name contains query but doesn't start with it
    starts_with_ids = {c['id'] for c in starts_with}
    contains = list(
        base_qs.filter(name__icontains=q)
        .exclude(id__in=starts_with_ids)
        .values('id', 'name', 'phone')
        .order_by('name')[: max(0, 10 - len(starts_with))]
    )

    results = starts_with + contains
    return JsonResponse({'results': results})


@login_required
def customer_check_duplicate(request):
    """
    Exact-match duplicate check (case-insensitive) used when creating a new customer.
    Returns {'exists': bool, 'customer': {id, name, phone} | null}
    """
    name = request.GET.get('name', '').strip()
    if not name:
        return JsonResponse({'exists': False, 'customer': None})

    try:
        customer = Customer.objects.get(owner=request.user, name__iexact=name)
        return JsonResponse({
            'exists': True,
            'customer': {
                'id': customer.pk,
                'name': customer.name,
                'phone': customer.phone or '',
            }
        })
    except Customer.DoesNotExist:
        return JsonResponse({'exists': False, 'customer': None})



# ── Public Receipt View (no login required) ───────────────────────────────────
def transaction_receipt(request, token):
    import qrcode, io, base64
    txn = get_object_or_404(Transaction, receipt_token=token)

    # Build QR as plain text — works offline, no internet needed for customer
    items = txn.items.all()
    payments = txn.payments.all()

    lines = []
    lines.append("=== UtangTracker Receipt ===")
    lines.append(f"Transaction #: {txn.pk}")
    lines.append(f"Customer     : {txn.customer.name}")
    if txn.customer.phone:
        lines.append(f"Phone        : {txn.customer.phone}")
    lines.append(f"Date         : {txn.date}")
    lines.append("---------------------------")
    lines.append("ITEMS:")
    for item in items:
        lines.append(f"  {item.item_name} x{item.quantity} {item.unit} @ P{item.price} = P{item.subtotal()}")
    lines.append("---------------------------")
    lines.append(f"Total Charged: P{txn.total_amount()}")
    if payments:
        lines.append("PAYMENTS:")
        for p in payments:
            note = f" ({p.note})" if p.note else ""
            lines.append(f"  {p.date}{note}: P{p.amount}")
        lines.append(f"Total Paid   : P{txn.total_paid()}")
    lines.append(f"BALANCE DUE  : P{txn.remaining_balance()}")
    lines.append("---------------------------")
    if txn.status == 'paid':
        lines.append("STATUS: FULLY PAID")
    elif txn.status == 'partial':
        lines.append("STATUS: PARTIALLY PAID")
    else:
        lines.append("STATUS: UNPAID")
    if txn.promise_date:
        lines.append(f"Promise Date : {txn.promise_date}")
    if txn.notes:
        lines.append(f"Notes        : {txn.notes}")
    lines.append("===========================")

    qr_text = "\n".join(lines)

    qr = qrcode.QRCode(
        version=None,
        box_size=6,
        border=3,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
    )
    qr.add_data(qr_text)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#1c2e4a", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    qr_b64 = base64.b64encode(buf.getvalue()).decode()

    import json
    return render(request, 'tracker/receipt.html', {
        'txn': txn,
        'items': items,
        'payments': payments,
        'qr_b64': qr_b64,
        'qr_text': qr_text,
        'qr_text_json': json.dumps(qr_text),
    })
