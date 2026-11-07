from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages


def vendor_required(view_func):
    """فقط کاربری که Vendor فعال داره اجازه دسترسی داره"""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('accounts:login')

        if not hasattr(request.user, 'vendor') or request.user.vendor is None:
            messages.error(request, "شما دسترسی به پنل فروشنده ندارید.")
            return redirect('catalog:home')

        if not request.user.vendor.is_active:
            messages.warning(request, "فروشگاه شما هنوز تایید نشده است.")
            return redirect('catalog:home')

        return view_func(request, *args, **kwargs)
    return wrapper