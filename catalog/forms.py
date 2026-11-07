from django import forms
from django.core.exceptions import ValidationError
from django.utils.text import slugify
from .models import Product, ProductImage


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['name', 'slug', 'category', 'description', 'price', 'stock', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-input'}),
            'slug': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'مثلاً: samsung-a54'}),
            'category': forms.Select(attrs={'class': 'form-input'}),
            'description': forms.Textarea(attrs={'class': 'form-input', 'rows': 4}),
            'price': forms.NumberInput(attrs={'class': 'form-input'}),
            'stock': forms.NumberInput(attrs={'class': 'form-input'}),
        }

    def __init__(self, *args, vendor=None, **kwargs):
        super().__init__(*args, **kwargs)
        if vendor:
            self.fields['category'].queryset = vendor.categories.all()

    def clean_slug(self):
        slug = self.cleaned_data.get('slug')
        if slug:
            slug = slugify(slug, allow_unicode=False)
        return slug


class ProductImageForm(forms.ModelForm):
    MAX_SIZE_MB = 3

    class Meta:
        model = ProductImage
        fields = ['image', 'alt_text', 'is_main']
        widgets = {
            'image': forms.FileInput(attrs={'class': 'form-input', 'accept': 'image/*'}),
            'alt_text': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'مثلاً: گوشی سامسونگ A54 از نمای جلو'
            }),
        }

    def clean_image(self):
        image = self.cleaned_data.get('image')
        if image:
            if image.size > self.MAX_SIZE_MB * 1024 * 1024:
                raise ValidationError(f"حجم تصویر نباید بیشتر از {self.MAX_SIZE_MB} مگابایت باشد.")
            valid_types = ['image/jpeg', 'image/png', 'image/webp', 'image/gif']
            if hasattr(image, 'content_type') and image.content_type not in valid_types:
                raise ValidationError("فقط فرمت‌های JPG، PNG، WEBP و GIF مجاز هستند.")
        return image

