from django.db import models
from django.contrib.auth.models import User
from django_jalali.db import models as jmodels

class Vendor(models.Model):
    owner = models.OneToOneField(
        User, on_delete=models.PROTECT,
        related_name='vendor', null=True, blank=True,
        verbose_name="مالک فروشگاه"
    )
    name = models.CharField(max_length=100, verbose_name="نام فروشگاه")
    legal_name = models.CharField(max_length=200, verbose_name="نام حقوقی شرکت")
    national_id = models.CharField(max_length=20, unique=True, verbose_name="شناسه ملی")
    subdomain = models.SlugField(max_length=50, unique=True, verbose_name="زیردامنه")
    is_active = models.BooleanField(default=False, verbose_name="فعال شده")
    commission_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0.0, verbose_name="درصد کمیسیون")
    created_at = jmodels.jDateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    zarinpal_merchant_id = models.CharField(
        max_length=36, blank=True, null=True,
        verbose_name="مرچنت کد زرین‌پال",
        help_text="شناسه ۳۶ کاراکتری اختصاصی این فروشنده در زرین‌پال"
    )
#######