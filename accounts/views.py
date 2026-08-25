from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.core.mail import send_mail
from django.template.loader import render_to_string
from .forms import SignUpForm, EmailLoginForm, ForgotPasswordForm, SetNewPasswordForm


def login_view(request):
    if request.method == 'POST':
        form = EmailLoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data.get('email')
            password = form.cleaned_data.get('password')
            try:
                user_obj = User.objects.get(email=email)
                username = user_obj.username
            except User.DoesNotExist:
                username = None

            user = authenticate(request, username=username, password=password) if username else None
            if user is not None:
                login(request, user)
                return redirect('dashboard_home')
            else:
                return render(request, 'accounts/login.html', {'form': form, 'error': 'البريد الإلكتروني أو كلمة المرور غير صحيحة'})
    else:
        form = EmailLoginForm()
    return render(request, 'accounts/login.html', {'form': form})


def logout_view(request):
    logout(request)
    return redirect('login')


@login_required
def home_view(request):
    return render(request, 'accounts/home.html', {'user': request.user})


def signup_view(request):
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('dashboard_home')
    else:
        form = SignUpForm()
    return render(request, 'accounts/signup.html', {'form': form})


def forgot_password_view(request):
    sent = False
    if request.method == 'POST':
        form = ForgotPasswordForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data.get('email')
            try:
                user = User.objects.get(email=email)
                uid = urlsafe_base64_encode(force_bytes(user.pk))
                token = default_token_generator.make_token(user)
                reset_link = request.build_absolute_uri(f'/accounts/reset-password/{uid}/{token}/')

                send_mail(
                    subject='إعادة تعيين كلمة المرور - EnerTrack',
                    message=f'اضغط على الرابط التالي لإعادة تعيين كلمة المرور:\n{reset_link}',
                    from_email=None,
                    recipient_list=[email],
                    fail_silently=False,
                )
            except User.DoesNotExist:
                pass
            sent = True
    else:
        form = ForgotPasswordForm()
    return render(request, 'accounts/forgot_password.html', {'form': form, 'sent': sent})


def reset_password_view(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is not None and default_token_generator.check_token(user, token):
        if request.method == 'POST':
            form = SetNewPasswordForm(request.POST)
            if form.is_valid():
                user.set_password(form.cleaned_data['password1'])
                user.save()
                return redirect('login')
        else:
            form = SetNewPasswordForm()
        return render(request, 'accounts/reset_password.html', {'form': form, 'valid_link': True})
    else:
        return render(request, 'accounts/reset_password.html', {'valid_link': False})
