from django.db import models
from django.contrib.auth.models import User
from catalog.models import Product
from vendors.models import Vendor
from django.utils import timezone
from django_jalali.db import models as jmodels

class Cart(models.Model):
    """سبد خرید — برای کاربر لاگین‌کرده یا مهمان (با session_key)"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='carts')
    session_key = models.CharField(max_length=40, null=True, blank=True)
    created_at = jmodels.jDateTimeField(auto_now_add=True)
    updated_at = jmodels.jDateTimeField(auto_now=True)

    def __str__(self):
        return f"Cart #{self.id} — {self.user or self.session_key}"

    @property
    def total_items(self):
        return sum(item.quantity for item in self.items.all())

    @property
    def total_price(self):
        return sum(item.subtotal for item in self.items.all())

    def items_by_vendor(self):
        """گروه‌بندی اقلام بر اساس فروشنده — برای پرداخت مستقیم به هر فروشنده"""
        result = {}
        for item in self.items.select_related('product__vendor'):
            vendor = item.product.vendor
            result.setdefault(vendor, []).append(item)
        return result


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    added_at = jmodels.jDateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('cart', 'product')  # هر محصول یک ردیف در سبد

    @property
    def subtotal(self):
        return self.product.price * self.quantity

    def __str__(self):
        return f"{self.product.name} × {self.quantity}"

class Order(models.Model):
    """سفارش — هر سفارش به یک فروشنده تعلق داره"""
    STATUS_CHOICES = [
        ('pending', 'در انتظار پرداخت'),
        ('paid', 'پرداخت شده'),
        ('processing', 'در حال پردازش'),
        ('shipped', 'ارسال شده'),
        ('delivered', 'تحویل شده'),
        ('cancelled', 'لغو شده'),
    ]

    user = models.ForeignKey(User, on_delete=models.PROTECT, related_name='orders')
    vendor = models.ForeignKey(Vendor, on_delete=models.PROTECT, related_name='orders')
    order_number = models.CharField(max_length=20, unique=True)

    # اطلاعات گیرنده (snapshot در لحظه سفارش)
    receiver_name = models.CharField(max_length=100)
    receiver_phone = models.CharField(max_length=15)
    shipping_province = models.CharField(max_length=50)
    shipping_city = models.CharField(max_length=50)
    shipping_postal_code = models.CharField(max_length=10)
    shipping_address = models.TextField()

    # مبالغ
    subtotal = models.DecimalField(max_digits=12, decimal_places=0)
    shipping_cost = models.DecimalField(max_digits=10, decimal_places=0, default=0)
    total = models.DecimalField(max_digits=12, decimal_places=0)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    tracking_code = models.CharField(max_length=50, blank=True)
    notes = models.TextField(blank=True)

    created_at = jmodels.jDateTimeField(auto_now_add=True)
    updated_at = jmodels.jDateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.order_number} — {self.vendor.name}"

    payment_authority = models.CharField(max_length=100, blank=True, null=True, verbose_name="Authority پرداخت")
    payment_ref_id = models.CharField(max_length=100, blank=True, null=True, verbose_name="شماره تراکنش (RefID)")
    paid_at = jmodels.jDateTimeField(blank=True, null=True, verbose_name="زمان پرداخت")
    settled_at = jmodels.jDateTimeField(blank=True, null=True, verbose_name="زمان تسویه")
    coupon = models.ForeignKey('Coupon', on_delete=models.SET_NULL, null=True, blank=True, related_name='orders')
    discount_amount = models.DecimalField(max_digits=12, decimal_places=0, default=0, verbose_name="مبلغ تخفیف")


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True)
    # snapshot — قیمت و نام رو نگه می‌داریم چون ممکنه بعداً تغییر کنه
    product_name = models.CharField(max_length=200)
    unit_price = models.DecimalField(max_digits=12, decimal_places=0)
    quantity = models.PositiveIntegerField()
    total_price = models.DecimalField(max_digits=12, decimal_places=0)

    def __str__(self):
        return f"{self.product_name} × {self.quantity}"

class VendorSettlement(models.Model):
    """تسویه‌ی دوره‌ای با فروشنده"""
    STATUS_CHOICES = [
        ('draft', 'پیش‌نویس'),
        ('paid', 'پرداخت شده'),
        ('cancelled', 'لغو شده'),
    ]

    vendor = models.ForeignKey(Vendor, on_delete=models.PROTECT, related_name='settlements')
    period_start = jmodels.jDateField(verbose_name="از تاریخ")
    period_end = jmodels.jDateField(verbose_name="تا تاریخ")

    total_sales = models.DecimalField(max_digits=14, decimal_places=0, default=0, verbose_name="کل فروش")
    commission = models.DecimalField(max_digits=14, decimal_places=0, default=0, verbose_name="کمیسیون سایت")
    net_payable = models.DecimalField(max_digits=14, decimal_places=0, default=0, verbose_name="مبلغ قابل پرداخت")

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    reference_no = models.CharField(max_length=100, blank=True, verbose_name="شماره پیگیری بانکی")
    notes = models.TextField(blank=True, verbose_name="یادداشت")
    paid_at = jmodels.jDateTimeField(blank=True, null=True)

    created_by = models.ForeignKey(
        'auth.User', on_delete=models.SET_NULL, null=True,
        related_name='created_settlements', verbose_name="ثبت‌کننده"
    )
    created_at = jmodels.jDateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = "Vendor Settlements"

    def __str__(self):
        return f"{self.vendor.name} — {self.period_start} تا {self.period_end}"

class Coupon(models.Model):
    """کد تخفیف — متعلق به یک فروشنده"""
    DISCOUNT_TYPE_CHOICES = [
        ('percent', 'درصدی'),
        ('fixed', 'مبلغ ثابت'),
    ]

    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, related_name='coupons')
    code = models.CharField(max_length=30, verbose_name="کد تخفیف")
    discount_type = models.CharField(max_length=10, choices=DISCOUNT_TYPE_CHOICES, default='percent')
    discount_value = models.DecimalField(max_digits=10, decimal_places=0, verbose_name="مقدار تخفیف")

    min_purchase = models.DecimalField(max_digits=12, decimal_places=0, default=0, verbose_name="حداقل مبلغ خرید")
    max_discount = models.DecimalField(max_digits=12, decimal_places=0, null=True, blank=True, verbose_name="سقف تخفیف (برای درصدی)")

    max_uses = models.PositiveIntegerField(default=0, verbose_name="حداکثر استفاده (۰ = نامحدود)")
    used_count = models.PositiveIntegerField(default=0, verbose_name="تعداد استفاده‌شده")

    valid_from = jmodels.jDateTimeField(verbose_name="معتبر از")
    valid_until = jmodels.jDateTimeField(verbose_name="معتبر تا")

    is_active = models.BooleanField(default=True, verbose_name="فعال")
    created_at = jmodels.jDateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('vendor', 'code')   # کد در هر فروشنده یکتاست
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.code} — {self.vendor.name}"

    @property
    def is_valid(self):
        """آیا کد الان قابل استفاده‌ست؟"""
        now = timezone.now()
        if not self.is_active:
            return False
        if self.valid_from > now or self.valid_until < now:
            return False
        if self.max_uses > 0 and self.used_count >= self.max_uses:
            return False
        return True

    def calculate_discount(self, subtotal):
        """محاسبه مبلغ تخفیف برای یک مبلغ سبد"""
        if subtotal < self.min_purchase:
            return 0

        if self.discount_type == 'percent':
            discount = float(subtotal) * (float(self.discount_value) / 100)
            if self.max_discount:
                discount = min(discount, float(self.max_discount))
        else:
            discount = float(self.discount_value)

        # تخفیف بیشتر از مبلغ سبد نمی‌شه
        return min(int(discount), int(subtotal))


class CouponUsage(models.Model):
    """ثبت استفاده از کد تخفیف (برای جلوگیری از استفاده مکرر یک کاربر)"""
    coupon = models.ForeignKey(Coupon, on_delete=models.CASCADE, related_name='usages')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='coupon_usages')
    order = models.ForeignKey('Order', on_delete=models.SET_NULL, null=True, blank=True)
    used_at = jmodels.jDateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('coupon', 'user')   # هر کاربر فقط یک‌بار می‌تونه از هر کد استفاده کنه
#######