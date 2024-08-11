from django.db import models
from accounts.models import UserBankAccount
from .constants import TRANSACTION_TYPE

class Transaction(models.Model):
    account = models.ForeignKey(UserBankAccount, related_name = 'transactions', on_delete = models.CASCADE)
    target_account = models.ForeignKey(UserBankAccount, related_name='incoming_transactions', on_delete=models.CASCADE, null=True, blank=True)
    
    amount = models.DecimalField(decimal_places=2, max_digits=10)
    balance_after_transaction = models.DecimalField(decimal_places=2, max_digits=10)
    transaction_type = models.IntegerField(choices=TRANSACTION_TYPE, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    loan_approve = models.BooleanField(default=False)
    is_bankrupt = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['timestamp']
