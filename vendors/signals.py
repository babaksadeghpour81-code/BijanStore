from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import Vendor
from notifications.models import Notification


@receiver(post_save, sender=Vendor)
def notify_admin_new_vendor(sender, instance, created, **kwargs):
    """وقتی فروشنده جدید ساخته شد، به همه superuserها اعلان بفرست"""
    if created:
        admins = User.objects.filter(is_superuser=True)
        for admin in admins:
            Notification.send(
                user=admin,
                title=f"فروشنده جدید: {instance.name}",
                message=f"فروشنده «{instance.legal_name}» با شناسه ملی {instance.national_id} در سایت ثبت شد. برای بررسی و تأیید به پنل ادمین بروید.",
                type='vendor',
                link='/dashboard/vendors/',
            )

