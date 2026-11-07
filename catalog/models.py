from django.db import models
from vendors.models import Vendor
from django.utils.text import slugify
from django_jalali.db import models as jmodels

class Category(models.Model):
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, related_name='categories')
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=120, unique=True, blank=True, allow_unicode=True)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='children')

    class Meta:
        verbose_name_plural = "Categories"

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.name, allow_unicode=True) or f"cat"
            slug = base
            counter = 1
            while Category.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

class Product(models.Model):
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, related_name='products')
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, related_name='products')
    name = models.CharField(max_length=200, verbose_name="نام محصول")
    slug = models.SlugField(max_length=200)
    description = models.TextField(blank=True, verbose_name="توضیحات")
    price = models.DecimalField(max_digits=12, decimal_places=0, verbose_name="قیمت")
    stock = models.PositiveIntegerField(default=0, verbose_name="موجودی")
    is_active = models.BooleanField(default=True)
    created_at = jmodels.jDateTimeField(auto_now_add=True)   # ← جدید
    updated_at = jmodels.jDateTimeField(auto_now=True)       # ← جدید (اختیاری)

    @property
    def main_image(self):
        return self.images.filter(is_main=True).first() or self.images.first()

    def __str__(self):
        return self.name

class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='products/%Y/%m/', verbose_name="تصویر")
    alt_text = models.CharField(max_length=150, blank=True, verbose_name="متن جایگزین")
    is_main = models.BooleanField(default=False, verbose_name="تصویر اصلی")
    sort_order = models.PositiveSmallIntegerField(default=0, verbose_name="ترتیب")
    created_at = jmodels.jDateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-is_main', 'sort_order', 'id']

    def __str__(self):
        return f"{self.product.name} — {'اصلی' if self.is_main else self.id}"

    def save(self, *args, **kwargs):
        # اگر این تصویر به‌عنوان اصلی علامت خورده، بقیه رو از حالت اصلی خارج کن
        if self.is_main and self.product_id:
            ProductImage.objects.filter(
                product_id=self.product_id, is_main=True
            ).exclude(pk=self.pk).update(is_main=False)
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        # حذف فایل فیزیکی هم انجام بشه
        self.image.delete(save=False)
        super().delete(*args, **kwargs)
#######