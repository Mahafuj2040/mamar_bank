from django import forms
from .models import Transaction
from accounts.models import UserBankAccount

class TransactionForm(forms.ModelForm):
    class Meta:
        model = Transaction
        fields = ['amount', 'transaction_type']
    
    def __init__(self, *args, **kwargs):
        self.account = kwargs.pop('account')
        super().__init__(*args, **kwargs) # this line
        self.fields['transaction_type'].disabled = True
        self.fields['transaction_type'].widget = forms.HiddenInput
    
    def save(self, commit = True):
        self.instance.account = self.account
        self.instance.balance_after_transaction = self.account.balance
        return super().save()

class DepositForm(TransactionForm):
    def clean_amount(self):
        min_deposit_amount = 100
        amount = self.cleaned_data.get('amount')
        if amount < min_deposit_amount:
            raise forms.ValidationError(
                f'You need to deposit at least {min_deposit_amount} &'
            )
        return amount


class withdrawForm(TransactionForm):
    def clean_amount(self):
        account = self.account
        min_withdraw_amount = 500
        max_withdraw_amount = 20000
        balance = account.balance
        amount = self.cleaned_data.get('amount')
        
        if amount < min_withdraw_amount:
            raise forms.ValidationError(
                f'You can withdraw at least {min_withdraw_amount} &'
            )
        
        if amount > max_withdraw_amount:
            raise forms.ValidationError(
                f'You can withdraw at most {max_withdraw_amount}'
            )
        
        if amount > balance:
            raise forms.ValidationError(
                f'You have {balance} $ in your account. You can not withdraw more than your account balance'
            )
            
        return amount

class LoanRequestForm(TransactionForm):
    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        return amount


class TransferForm(forms.ModelForm):
    target_account_no = forms.CharField(max_length=8, required=True, label="Target Account Number")
    
    class Meta:
        model = Transaction
        fields = ['amount', 'target_account_no']
        
    def __init__(self, *args, **kwargs):
        self.account = kwargs.pop('account')
        super().__init__(*args, **kwargs)
        
    def clean_target_account_no(self):
        account_no = self.cleaned_data.get('target_account_no')
        try:
            target_account = UserBankAccount.objects.get(account_no = account_no)
        except UserBankAccount.DoesNotExist:
            raise forms.ValidationError(f'Account number {account_no} not found.')
        if target_account == self.account:
            raise forms.ValidationError("You cannot transfer your own account")
        return target_account
    
    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        
        if amount <= 0:
            raise forms.ValidationError("Amount must be grater than zero.")
        if amount > self.account.balance:
            raise forms.ValidationError(f"Insufficient balance. Your current balance is {self.account.balance}")
        return amount
    
    def save(self, commit=True):
        target_account = self.cleaned_data.get('target_account_no')
        self.instance.account = self.account
        self.instance.target_account = target_account
        self.instance.balance_after_transaction = self.account.balance - self.cleaned_data.get('amount')
        return super().save(commit)
