from .utils import get_or_create_cart


def cart_info(request):
    try:
        cart = get_or_create_cart(request)
        return {'cart_count': cart.total_items}
    except Exception:
        return {'cart_count': 0}