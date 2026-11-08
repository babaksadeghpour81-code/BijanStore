from django.db import models
from django.contrib.auth.models import User
from django_jalali.db import models as jmodels

class Notification(models.Model):
    """اعلان داخل‌سایتی برای کاربران"""

    TYPE_CHOICES = [
        ('order_status', 'تغییر وضعیت سفارش'),
        ('payment', 'پرداخت'),
        ('coupon', 'کد تخفیف'),
        ('vendor', 'فروشنده'),
        ('settlement', 'تسویه'),
        ('system', 'سیستمی'),
    ]

    user = models.ForeignKey(
        User, on_delete=models.CASCADE,
        related_name='notifications', verbose_name="کاربر"
    )
    type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='system')
    title = models.CharField(max_length=200, verbose_name="عنوان")
    message = models.TextField(verbose_name="متن")
    link = models.CharField(max_length=300, blank=True, verbose_name="لینک")
    is_read = models.BooleanField(default=False, verbose_name="خوانده‌شده")
    created_at = jmodels.jDateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = "Notifications"

    def __str__(self):
        return f"{self.user.username} — {self.title}"

    @classmethod
    def send(cls, user, title, message, type='system', link='', send_email=True):
        """ساخت اعلان + ارسال ایمیل"""
        notification = cls.objects.create(
            user=user, title=title, message=message,
            type=type, link=link
        )

        if send_email:
            from .emails import send_notification_email
            send_notification_email(user, title, message, link)

        return notification
#######