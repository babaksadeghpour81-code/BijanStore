from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags


def send_notification_email(user, title, message, link=''):
    """ارسال ایمیل اعلان به کاربر"""
    if not user.email:
        return False

    # ساخت لینک کامل
    full_link = ''
    if link:
        # اگر لینک نسبی بود، دامنه رو اضافه کن
        if link.startswith('/'):
            full_link = f"http://127.0.0.1:8000{link}"   # در پروداکشن، دامنه واقعی
        else:
            full_link = link

    # متن ایمیل
    subject = f"[BijanStore] {title}"
    text_message = f"""
سلام {user.get_full_name() or user.username} عزیز،

{message}

{f"برای مشاهده جزئیات: {full_link}" if full_link else ""}

---
این ایمیل به‌صورت خودکار از طرف BijanStore ارسال شده است.
لطفاً به این ایمیل پاسخ ندهید.
"""

    try:
        send_mail(
            subject=subject,
            message=text_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=True,   # اگر خطا داد، کرش نکن
        )
        return True
    except Exception as e:
        print(f"[EMAIL ERROR] {e}")
        return False