from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import CreateView, ListView, View
from .models import Transaction
from django.core.mail import EmailMessage, EmailMultiAlternatives
from django.template.loader import render_to_string
from django.urls import reverse_lazy
from .constants import DEPOSIT, LOAN, LOAN_PAID, WITHDRAWAL, TRANSFER
from django.contrib import messages
from .forms import(
    DepositForm,
    withdrawForm, 
    LoanRequestForm,
    TransferForm,
)
from django.http import HttpResponse
from datetime import datetime
from django.db.models import Sum


def send_transaction_email(user, amount, subject, template, recipient_email=None, recipient_name=None):
    message = render_to_string(template, {
        'user': user,
        'amount': amount,
    })
    
   
    send_email = EmailMultiAlternatives(subject, '', to=[user.email])
    send_email.attach_alternative(message, "text/html")
    send_email.send()

    if recipient_email:
        recipient_message = render_to_string('transactions/recipient_email.html', {
            'user': user,
            'recipient_name': recipient_name,
            'amount': amount,
        })

        recipient_subject = "You've received a transfer"
        send_recipient_email = EmailMultiAlternatives(recipient_subject, '', to=[recipient_email])
        send_recipient_email.attach_alternative(recipient_message, "text/html")
        send_recipient_email.send()


class TransactionCreateMixin(LoginRequiredMixin, CreateView):
    template_name = 'transactions/transaction_form.html'
    model = Transaction
    title = ''
    success_url = reverse_lazy('transaction_report')
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({
            'account' : self.request.user.account
        })
        return kwargs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'title' : self.title
        })
        return context

    
    
class DepositMoneyView(TransactionCreateMixin):
    form_class = DepositForm 
    title = 'Deposit'
    
    def get_initial(self):
        initial = {'transaction_type' : DEPOSIT}
        return initial
    
    def form_valid(self, form):
        amount = form.cleaned_data.get('amount')
        account = self.request.user.account
        account.balance += amount
        account.save(
            update_fields=['balance']
        )
        messages.success(
            self.request,
            f'{"{:,.2f}".format(float(amount))}$ was deposited to your account successfully'
        )
        send_transaction_email(self.request.user, amount, "Deposit Message", 'transactions/deposit_email.html')
        return super().form_valid(form)


class WithdrawMoneyView(TransactionCreateMixin):
    form_class = withdrawForm
    title = 'Withdraw Money'
    
    def get_initial(self):
        initial = {'transaction_type' : WITHDRAWAL}
        return initial
    
    def form_valid(self, form):
        amount = form.cleaned_data.get('amount')
        self.request.user.account.balance -= form.cleaned_data.get('amount')
        self.request.user.account.save(update_fields=['balance'])
        
        messages.success(
            self.request,
            f'Successfully withdrawn {"{:,.2f}".format(float(amount))}$ from your account'
        )
        send_transaction_email(self.request.user, amount, "Withdraw Message", 'transactions/withdraw_email.html')
        return super().form_valid(form)

class LoanRequestView(TransactionCreateMixin):
    form_class = LoanRequestForm
    title = 'Request For Loan'

    def get_initial(self):
        initial = {'transaction_type': LOAN}
        return initial

    def form_valid(self, form):
        amount = form.cleaned_data.get('amount')
        current_loan_count = Transaction.objects.filter(
            account=self.request.user.account,transaction_type=3).count()
        print(current_loan_count)
        if current_loan_count >= 3:
            return HttpResponse("You have cross the loan limits")
        
        
        messages.success(
            self.request,
            f'Loan request for {"{:,.2f}".format(float(amount))}$ submitted successfully'
        )
        send_transaction_email(self.request.user, amount, "Loan Request Message", 'transactions/loanRequest_email.html')
        return super().form_valid(form)


class TransactionReportView(LoginRequiredMixin, ListView):
    template_name = 'transactions/transaction_report.html'
    model = Transaction
    balance = 0 
    
    def get_queryset(self):
        queryset = super().get_queryset().filter(
            account=self.request.user.account
        )
        start_date_str = self.request.GET.get('start_date')
        end_date_str = self.request.GET.get('end_date')
        
        if start_date_str and end_date_str:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            
            queryset = queryset.filter(timestamp__date__gte=start_date, timestamp__date__lte=end_date)
            self.balance = Transaction.objects.filter(
                timestamp__date__gte=start_date, timestamp__date__lte=end_date
            ).aggregate(Sum('amount'))['amount__sum']
        else:
            self.balance = self.request.user.account.balance
       
        return queryset.distinct() 
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'account': self.request.user.account
        })

        return context

class PayLoanView(LoginRequiredMixin, View):
    def get(self, request, loan_id):
        loan = get_object_or_404(Transaction, id=loan_id)
        if loan.transaction_type == LOAN and loan.loan_approve:
            user_account = loan.account

            if loan.amount <= user_account.balance:
                user_account.balance -= loan.amount
                user_account.save()
                loan.loan_approve = False
                loan.transaction_type = LOAN_PAID
                loan.save() 

                messages.success(
                    self.request,
                    f'Loan of {"{:,.2f}".format(float(loan.amount))}$ paid successfully'
                )
            else:
                messages.error(
                    self.request,
                    f'Insufficient balance to pay the loan'
                )
        else:
            messages.error(
                self.request,
                'Loan is either already paid or not valid'
            )
        return redirect('loan_list')

class LoanListView(LoginRequiredMixin, ListView):
    model = Transaction
    template_name = 'transactions/loan_request.html'
    context_object_name = 'loans'

    def get_queryset(self):
        user_account = self.request.user.account
        return Transaction.objects.filter(
            account=user_account,
            transaction_type=LOAN,
        )


class TransferMoneyView(LoginRequiredMixin, View):
    template_name = 'transactions/transfer_form.html'
    success_url = reverse_lazy('transaction_report')
    
    #get request
    def get(self, request, *args, **kwargs):
        form = TransferForm(account=request.user.account)
        context = {
            'form': form,
            'title': 'Transfer Money'
        }
        return render(request, self.template_name, context)
    
    #post Request
    def post(self, request, *args, **kwargs):
        form = TransferForm(request.POST, account=request.user.account)
        if form.is_valid():
            amount = form.cleaned_data.get('amount')
            target_account = form.cleaned_data.get('target_account_no')

            if request.user.account.balance >= amount:
                request.user.account.balance -= amount
                request.user.account.save(update_fields=['balance'])

                target_account.balance += amount
                target_account.save(update_fields=['balance'])

                #sender transaction update
                sender_transaction = form.save(commit=False)
                sender_transaction.account = request.user.account
                sender_transaction.transaction_type = TRANSFER
                sender_transaction.amount = -amount
                sender_transaction.balance_after_transaction = request.user.account.balance
                sender_transaction.save()

                #recipient transaction update
                recipient_transaction = Transaction.objects.create(
                    account=target_account,
                    transaction_type=TRANSFER,
                    amount=amount, 
                    balance_after_transaction=target_account.balance, 
                    timestamp=sender_transaction.timestamp 
                )

                #email send
                send_transaction_email(
                    request.user, 
                    amount, 
                    "Transfer Confirmation", 
                    'transactions/transfer_email.html', 
                    recipient_email=target_account.user.email, 
                    recipient_name=target_account.user.get_full_name()
                )

                # Show a success message
                messages.success(
                    request,
                    f'Successfully transferred {"{:,.2f}".format(float(amount))}$ to account {target_account.account_no}'
                )

                return redirect(self.success_url)
            else:
                messages.error(request, 'Insufficient balance for the transfer.')

        context = {
            'form': form,
            'title': 'Transfer Money',
        }
        return render(request, self.template_name, context)


# Updated code