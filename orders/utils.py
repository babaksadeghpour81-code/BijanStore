from .models import Cart


def get_or_create_cart(request):
    """
    سبد خرید کاربر جاری رو برمی‌گردونه.
    - اگر لاگین باشه: بر اساس user
    - اگر مهمان باشه: بر اساس session_key
    """
    if not request.session.session_key:
        request.session.create()

    if request.user.is_authenticated:
        cart, _ = Cart.objects.get_or_create(user=request.user, defaults={'session_key': None})
    else:
        cart, _ = Cart.objects.get_or_create(session_key=request.session.session_key, user=None)

    return cart


def merge_guest_cart_to_user(request, user):
    """وقتی مهمان لاگین کرد، سبدش رو به سبد کاربر منتقل کن"""
    if not request.session.session_key:
        return

    try:
        guest_cart = Cart.objects.get(session_key=request.session.session_key, user=None)
    except Cart.DoesNotExist:
        return

    user_cart, _ = Cart.objects.get_or_create(user=user)

    for item in guest_cart.items.all():
        existing, created = user_cart.items.get_or_create(
            product=item.product,
            defaults={'quantity': item.quantity}
        )
        if not created:
            existing.quantity += item.quantity
            existing.save()

    guest_cart.delete()