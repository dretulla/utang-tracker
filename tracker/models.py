from django.db import models
import uuid
from django.contrib.auth.models import User
from django.utils import timezone
from decimal import Decimal
import hashlib


# ─── Security / Account Recovery ─────────────────────────────────────────────

SECURITY_QUESTIONS = [
    ('fav_food',       "What is your favorite food?"),
    ('mothers_maiden', "What is your mother's maiden name?"),
    ('childhood_pet',  "What was the name of your first pet?"),
    ('birth_city',     "In what city were you born?"),
    ('fathers_bday',   "What is your father's birthday? (e.g. Jan 1)"),
    ('mothers_bday',   "What is your mother's birthday? (e.g. Jan 1)"),
    ('first_school',   "What was the name of your first school?"),
    ('fav_teacher',    "What is the name of your favorite teacher?"),
    ('childhood_hero', "Who was your childhood hero?"),
    ('custom',         "Custom question (write your own)"),
]


class UserSecurityProfile(models.Model):
    """Stores 2 security Q&A hashes per user for account recovery."""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='security_profile')

    question_1 = models.CharField(max_length=20, choices=SECURITY_QUESTIONS)
    custom_question_1 = models.CharField(max_length=200, blank=True, null=True)
    answer_1_hash = models.CharField(max_length=64)   # SHA-256 hex

    question_2 = models.CharField(max_length=20, choices=SECURITY_QUESTIONS)
    custom_question_2 = models.CharField(max_length=200, blank=True, null=True)
    answer_2_hash = models.CharField(max_length=64)

    created_at = models.DateTimeField(auto_now_add=True)

    @staticmethod
    def hash_answer(answer: str) -> str:
        """Normalise (lowercase, strip) then SHA-256."""
        normalised = answer.strip().lower()
        return hashlib.sha256(normalised.encode('utf-8')).hexdigest()

    def check_answer_1(self, answer: str) -> bool:
        return self.answer_1_hash == self.hash_answer(answer)

    def check_answer_2(self, answer: str) -> bool:
        return self.answer_2_hash == self.hash_answer(answer)

    def get_question_1_text(self):
        if self.question_1 == 'custom':
            return self.custom_question_1 or "Custom question"
        return dict(SECURITY_QUESTIONS).get(self.question_1, self.question_1)

    def get_question_2_text(self):
        if self.question_2 == 'custom':
            return self.custom_question_2 or "Custom question"
        return dict(SECURITY_QUESTIONS).get(self.question_2, self.question_2)

    def __str__(self):
        return f"Security profile for {self.user.username}"


class Customer(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='customers')
    name = models.CharField(max_length=100)
    phone = models.CharField(max_length=20, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

    def total_balance(self):
        total = Decimal('0')
        for txn in self.transactions.all():
            total += txn.remaining_balance()
        return total

    def total_charged(self):
        return sum(t.total_amount() for t in self.transactions.all()) or Decimal('0')

    def total_paid(self):
        return sum(t.total_paid() for t in self.transactions.all()) or Decimal('0')

    def transaction_count(self):
        return self.transactions.count()

    def is_high_debt(self):
        return self.total_balance() >= 500

    def has_unpaid(self):
        return self.transactions.filter(status__in=['unpaid', 'partial']).exists()


def default_transaction_time():
    return timezone.localtime().time()


class Transaction(models.Model):
    STATUS_CHOICES = [
        ('unpaid', 'Unpaid'),
        ('partial', 'Partially Paid'),
        ('paid', 'Fully Paid'),
    ]

    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='transactions')
    date = models.DateField(default=timezone.now)
    time = models.TimeField(default=default_transaction_time)
    notes = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='unpaid')
    promise_date = models.DateField(blank=True, null=True)
    promise_time = models.TimeField(blank=True, null=True)
    receipt_token = models.CharField(max_length=36, unique=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date', '-created_at']

    def save(self, *args, **kwargs):
        if not self.receipt_token:
            self.receipt_token = str(uuid.uuid4())
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.customer.name} — {self.date}"

    def total_amount(self):
        return sum(item.subtotal() for item in self.items.all()) or Decimal('0')

    def total_paid(self):
        result = self.payments.aggregate(models.Sum('amount'))['amount__sum']
        return result or Decimal('0')

    def remaining_balance(self):
        return self.total_amount() - self.total_paid()

    def update_status(self):
        balance = self.remaining_balance()
        paid = self.total_paid()
        if balance <= 0:
            self.status = 'paid'
        elif paid > 0:
            self.status = 'partial'
        else:
            self.status = 'unpaid'
        self.save(update_fields=['status'])


class TransactionItem(models.Model):
    UNIT_CHOICES = [
        ('qty', 'Qty'),
        ('kg', 'Kg'),
    ]

    transaction = models.ForeignKey(Transaction, on_delete=models.CASCADE, related_name='items')
    item_name = models.CharField(max_length=200)
    quantity = models.DecimalField(max_digits=8, decimal_places=2, default=1)
    unit = models.CharField(max_length=3, choices=UNIT_CHOICES, default='qty')
    price = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.item_name} x{self.quantity}"

    def subtotal(self):
        return self.quantity * self.price


class TransactionPayment(models.Model):
    transaction = models.ForeignKey(Transaction, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    date = models.DateField(default=timezone.now)
    paid_time = models.TimeField(blank=True, null=True)
    note = models.CharField(max_length=255, blank=True, null=True)
    receipt_token = models.CharField(max_length=36, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date', '-created_at']

    def save(self, *args, **kwargs):
        if not self.receipt_token:
            self.receipt_token = str(uuid.uuid4())
        super().save(*args, **kwargs)

    def __str__(self):
        return f"₱{self.amount} on {self.date}"
