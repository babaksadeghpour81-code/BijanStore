from django.shortcuts import redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from irgateway.zarinpal import ZarinpalClient
from irgateway.zarinpal.enums import Environment
from irgateway.zarinpal.errors import ZarinpalException
from django.conf import settings
from .models import Order
from notifications.models import Notification


def _get_client(merchant_id):
    """ساخت کلاینت زرین‌پال با مرچنت کد فروشنده"""
    env = Environment.SANDBOX if settings.ZARINPAL_SANDBOX else Environment.PRODUCTION
    return ZarinpalClient(merchant_id=merchant_id, environment=env)


@login_required
def payment_start(request, order_number):
    """
    شروع پرداخت برای یک سفارش
    """
    order = get_object_or_404(Order, order_number=order_number, user=request.user)

    if order.status != 'pending':
        messages.warning(request, "این سفارش قبلاً پرداخت شده یا لغو شده است.")
        return redirect('orders:order_detail', order_number=order.order_number)

    vendor = order.vendor
    if not vendor.zarinpal_merchant_id:
        messages.error(request, "فروشنده هنوز درگاه پرداخت را تنظیم نکرده است.")
        return redirect('orders:order_detail', order_number=order.order_number)

    client = _get_client(vendor.zarinpal_merchant_id)

    callback_url = f"{settings.ZARINPAL_CALLBACK_BASE}/cart/payment/callback/{order.order_number}/"

    try:
        payment = client.request(
            amount=int(order.total) * 10,   # تومان → ریال
            callback_url=callback_url,
            description=f"پرداخت سفارش {order.order_number}",
        )
        order.payment_authority = payment.authority
        order.save()
        return redirect(payment.payment_url)
    except ZarinpalException as e:
        messages.error(request, f"خطا در اتصال به درگاه: {e.message}")
        return redirect('orders:order_detail', order_number=order.order_number)


@login_required
def payment_callback(request, order_number):
    """
    بازگشت از درگاه و تأیید پرداخت
    """
    order = get_object_or_404(Order, order_number=order_number, user=request.user)

    authority = request.GET.get('Authority')
    status = request.GET.get('Status', 'NOK')

    if status != 'OK' or not authority:
        messages.warning(request, "پرداخت لغو شد یا ناموفق بود.")
        return redirect('orders:order_detail', order_number=order.order_number)

    if not order.vendor.zarinpal_merchant_id:
        messages.error(request, "مرچنت کد فروشنده یافت نشد.")
        return redirect('orders:order_detail', order_number=order.order_number)

    client = _get_client(order.vendor.zarinpal_merchant_id)

    try:
        verification = client.verify(
            authority=authority,
            amount=int(order.total) * 10,   # تومان → ریال
        )

        # کد ۱۰۰ = تأیید موفق، کد ۱۰۱ = قبلاً تأیید شده (هر دو موفق)
        if verification.code in [100, 101]:
            order.status = 'paid'
            order.payment_ref_id = str(verification.ref_id)
            order.paid_at = timezone.now()
            order.save()
            Notification.send(
                user=order.user,
                title=f"پرداخت سفارش {order.order_number} موفق بود",
                message=f"پرداخت شما با کد رهگیری {verification.ref_id} ثبت شد و فروشنده سفارش شما را آماده می‌کند.",
                type='payment',
                link=f"/cart/order/{order.order_number}/",
            )
            messages.success(request, f"پرداخت با موفقیت انجام شد. کد رهگیری: {verification.ref_id}")
        else:
            messages.error(request, f"پرداخت تأیید نشد. کد خطا: {verification.code}")
    except ZarinpalException as e:
        messages.error(request, f"خطا در تأیید پرداخت: {e.message}")

    return redirect('orders:order_detail', order_number=order.order_number)

