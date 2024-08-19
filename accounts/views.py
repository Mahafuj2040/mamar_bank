from django.shortcuts import render, redirect
from django.views.generic import FormView, View
from .forms import UserRegistrationForm, UserUpdateForm
from django.contrib.auth import login, logout
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView, LogoutView, PasswordChangeView
from django.contrib import messages

class UserRegistrationView(FormView):
    template_name = 'accounts/user_registration.html'  
    form_class = UserRegistrationForm
    success_url = reverse_lazy('profile')  
    
    def form_valid(self, form):
        user = form.save()
        login(self.request, user)
        return super().form_valid(form)
    
    
class UserLoginView(LoginView):
    template_name = 'accounts/user_login.html'
    
    def get_success_url(self):
        return reverse_lazy('home')


class UserLogoutView(LoginRequiredMixin, LogoutView):
    def get(self, request, *args, **kwargs):
        logout(request)
        return self.post(request, *args, **kwargs)

    def get_success_url(self):
        return reverse_lazy('home')


class UserBankAccountUpdateView(LoginRequiredMixin, View):
    template_name = 'accounts/profile.html'
    
    def get(self, request):
        form = UserUpdateForm(instance=request.user)
        return render(request, self.template_name, {'form': form})

    def post(self, request):
        form = UserUpdateForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            return redirect('profile')  
        return render(request, self.template_name, {'form': form})

class UserPasswordChangeView(LoginRequiredMixin, PasswordChangeView):
    template_name = 'accounts/password_change.html'
    success_url = reverse_lazy('profile')

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, "Your password has been successfully changed.")
        return response