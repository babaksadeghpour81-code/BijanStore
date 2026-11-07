from django import forms


class CheckoutForm(forms.Form):
    receiver_name = forms.CharField(
        max_length=100, label="نام و نام خانوادگی گیرنده",
        widget=forms.TextInput(attrs={'class': 'form-input'})
    )
    receiver_phone = forms.CharField(
        max_length=15, label="شماره تماس",
        widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': '09xxxxxxxxx'})
    )
    shipping_province = forms.CharField(
        max_length=50, label="استان",
        widget=forms.TextInput(attrs={'class': 'form-input'})
    )
    shipping_city = forms.CharField(
        max_length=50, label="شهر",
        widget=forms.TextInput(attrs={'class': 'form-input'})
    )
    shipping_postal_code = forms.CharField(
        max_length=10, label="کد پستی",
        widget=forms.TextInput(attrs={'class': 'form-input'})
    )
    shipping_address = forms.CharField(
        label="آدرس کامل",
        widget=forms.Textarea(attrs={'class': 'form-input', 'rows': 3})
    )
    notes = forms.CharField(
        required=False, label="توضیحات (اختیاری)",
        widget=forms.Textarea(attrs={'class': 'form-input', 'rows': 2})
    )