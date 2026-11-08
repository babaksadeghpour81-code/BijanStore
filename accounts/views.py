from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import RegisterForm, LoginForm
from orders.utils import merge_guest_cart_to_user
from django.core.mail import send_mail
from django.conf import settings
from django.urls import reverse
from django.template.loader import render_to_string
from .models import EmailConfirmation


def register_view(request):
    if request.user.is_authenticated:
        return redirect('catalog:home')

    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            # user.is_active = False   # تا تأیید نشه، غیرفعال
            user.is_active = True  # ← موقتاً True کن
            user.save()

            # ساخت توکن تأیید
            confirmation = EmailConfirmation.objects.create(user=user)

            # ارسال ایمیل تأیید
            confirm_link = request.build_absolute_uri(
                reverse('accounts:confirm_email', args=[str(confirmation.token)])
            )
            send_mail(
                subject='[BijanStore] تأیید ایمیل',
                message=f"""
سلام {user.get_full_name() or user.username} عزیز،

برای فعال‌سازی حساب خود در BijanStore، روی لینک زیر کلیک کنید:

{confirm_link}

اگر شما این ثبت‌نام را انجام نداده‌اید، این ایمیل را نادیده بگیرید.

---
BijanStore
                """,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=True,
            )

            messages.success(
                request,
                "ثبت‌نام انجام شد. لطفاً ایمیل خود را بررسی کنید و روی لینک تأیید کلیک کنید."
            )
            return redirect('accounts:login')
    else:
        form = RegisterForm()

    return render(request, 'accounts/register.html', {'form': form})


def confirm_email(request, token):
    """تأیید ایمیل با توکن"""
    try:
        confirmation = EmailConfirmation.objects.get(token=token)
    except EmailConfirmation.DoesNotExist:
        messages.error(request, "لینک تأیید نامعتبر است.")
        return redirect('accounts:login')

    if confirmation.is_confirmed:
        messages.info(request, "این ایمیل قبلاً تأیید شده است.")
        return redirect('accounts:login')

    # تأیید
    from django.utils import timezone
    confirmation.confirmed_at = timezone.now()
    confirmation.save()

    user = confirmation.user
    user.is_active = True
    user.save()

    login(request, user)
    messages.success(request, "ایمیل شما تأیید شد. خوش آمدید!")
    return redirect('catalog:home')


def login_view(request):
    if request.user.is_authenticated:
        return redirect('catalog:home')

    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            merge_guest_cart_to_user(request, user)
            messages.success(request, f"خوش آمدید {user.first_name}!")
            # ← ریدایرکت هوشمند
            if hasattr(user, 'vendor') and user.vendor and user.vendor.is_active:
                return redirect('vendors:dashboard')
            next_url = request.GET.get('next', 'catalog:home')
            return redirect(next_url)
        else:
            messages.error(request, "نام کاربری یا رمز عبور اشتباه است.")
    else:
        form = LoginForm()

    return render(request, 'accounts/login.html', {'form': form})


def logout_view(request):
    logout(request)
    messages.info(request, "با موفقیت خارج شدید.")
    return redirect('catalog:home')


@login_required
def profile_view(request):
    return render(request, 'accounts/profile.html')