from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User
from .models import (Customer, Transaction, TransactionItem,
                     TransactionPayment, UserSecurityProfile, SECURITY_QUESTIONS)


# ─── Auth ─────────────────────────────────────────────────────────────────────

class RegisterForm(UserCreationForm):
    question_1 = forms.ChoiceField(
        choices=SECURITY_QUESTIONS, label="Security Question 1",
        widget=forms.Select(attrs={'class': 'form-control', 'id': 'id_question_1'})
    )
    custom_question_1 = forms.CharField(
        required=False, label="Your custom question",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Write your own question…', 'id': 'id_custom_question_1'})
    )
    answer_1 = forms.CharField(
        label="Answer to Question 1",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Your answer (not case-sensitive)', 'autocomplete': 'off'})
    )
    question_2 = forms.ChoiceField(
        choices=SECURITY_QUESTIONS, label="Security Question 2",
        widget=forms.Select(attrs={'class': 'form-control', 'id': 'id_question_2'})
    )
    custom_question_2 = forms.CharField(
        required=False, label="Your custom question",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Write your own question…', 'id': 'id_custom_question_2'})
    )
    answer_2 = forms.CharField(
        label="Answer to Question 2",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Your answer (not case-sensitive)', 'autocomplete': 'off'})
    )

    class Meta:
        model = User
        fields = ['username', 'password1', 'password2']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Choose a username'})
        self.fields['password1'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Create a password'})
        self.fields['password2'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Confirm password'})

    def clean(self):
        cleaned = super().clean()
        q1 = cleaned.get('question_1')
        q2 = cleaned.get('question_2')
        if q1 == 'custom' and not cleaned.get('custom_question_1', '').strip():
            self.add_error('custom_question_1', 'Please enter your custom question.')
        if q2 == 'custom' and not cleaned.get('custom_question_2', '').strip():
            self.add_error('custom_question_2', 'Please enter your custom question.')
        if q1 and q2 and q1 == q2 and q1 != 'custom':
            self.add_error('question_2', 'Please choose a different question for Question 2.')
        if not cleaned.get('answer_1', '').strip():
            self.add_error('answer_1', 'Answer is required.')
        if not cleaned.get('answer_2', '').strip():
            self.add_error('answer_2', 'Answer is required.')
        return cleaned


class LoginForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Username'})
        self.fields['password'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Password'})


class RecoveryStep1Form(forms.Form):
    username = forms.CharField(
        label="Username",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter your username', 'autofocus': True})
    )

    def clean_username(self):
        username = self.cleaned_data['username'].strip()
        try:
            user = User.objects.get(username=username)
            if not hasattr(user, 'security_profile'):
                raise forms.ValidationError("This account has no security questions set up.")
        except User.DoesNotExist:
            raise forms.ValidationError("No account found with that username.")
        return username


class RecoveryStep2Form(forms.Form):
    answer_1 = forms.CharField(
        label="", widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Your answer…', 'autocomplete': 'off'})
    )
    answer_2 = forms.CharField(
        label="", widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Your answer…', 'autocomplete': 'off'})
    )


class RecoveryStep3Form(forms.Form):
    new_password1 = forms.CharField(
        label="New Password",
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Enter new password', 'autocomplete': 'new-password'})
    )
    new_password2 = forms.CharField(
        label="Confirm New Password",
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Confirm new password', 'autocomplete': 'new-password'})
    )

    def clean(self):
        cleaned = super().clean()
        p1 = cleaned.get('new_password1', '')
        p2 = cleaned.get('new_password2', '')
        if p1 and p2 and p1 != p2:
            self.add_error('new_password2', 'Passwords do not match.')
        if p1 and len(p1) < 8:
            self.add_error('new_password1', 'Password must be at least 8 characters.')
        return cleaned


# ─── Other Forms ─────────────────────────────────────────────────────────────

class CustomerForm(forms.ModelForm):
    class Meta:
        model = Customer
        fields = ['name', 'phone', 'notes']
        widgets = {
            'name':  forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Customer name'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '09xxxxxxxxx (optional)'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Notes (optional)', 'rows': 2}),
        }


class TransactionForm(forms.ModelForm):
    class Meta:
        model = Transaction
        fields = ['date', 'time', 'notes', 'promise_date', 'promise_time']
        widgets = {
            'date':         forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'time':         forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'notes':        forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Optional notes', 'rows': 2}),
            'promise_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'promise_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
        }


class TransactionItemForm(forms.ModelForm):
    class Meta:
        model = TransactionItem
        fields = ['item_name', 'quantity', 'unit', 'price']
        widgets = {
            'item_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Item name'}),
            'quantity':  forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '1', 'step': '0.01', 'min': '0.01'}),
            'unit':      forms.Select(attrs={'class': 'form-control'}),
            'price':     forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '0.00', 'step': '0.01', 'min': '0'}),
        }


class TransactionPaymentForm(forms.ModelForm):
    class Meta:
        model = TransactionPayment
        fields = ['amount', 'date', 'paid_time', 'note']
        widgets = {
            'amount':    forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '0.00', 'step': '0.01', 'min': '0.01'}),
            'date':      forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'paid_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'note':      forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Payment note (optional)'}),
        }
