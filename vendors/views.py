from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Sum, Count, Q
from orders.models import Order, OrderItem
from .decorators import vendor_required
from django.utils import timezone
from datetime import timedelta
from orders.models import VendorSettlement
from orders.models import Coupon
from notifications.models import Notification
import jdatetime

@vendor_required
def dashboard(request):
    vendor = request.user.vendor

    # همه سفارش‌های این فروشنده
    all_orders = Order.objects.filter(vendor=vendor)
    paid_orders = all_orders.filter(
        status__in=['paid', 'processing', 'shipped', 'delivered'],
        settled_at__isnull=True,
    )

    # آمار کلی
    total_orders = all_orders.count()
    pending_orders = all_orders.filter(status='pending').count()
    paid_orders_count = paid_orders.count()

    total_revenue = paid_orders.aggregate(total=Sum('total'))['total'] or 0

    # کل درآمد تاریخی (شامل تسویه‌شده‌ها)
    total_revenue_all_time = all_orders.filter(
        status__in=['paid', 'processing', 'shipped', 'delivered']
    ).aggregate(total=Sum('total'))['total'] or 0

    # کمیسیون
    commission = 0
    if vendor.commission_rate:
        commission = float(total_revenue) * (float(vendor.commission_rate) / 100)

    net_payable = int(float(total_revenue) - commission)

    # آمار زمانی
    now = timezone.now()
    last_7 = now - timedelta(days=7)
    last_30 = now - timedelta(days=30)

    revenue_7 = paid_orders.filter(created_at__gte=last_7).aggregate(total=Sum('total'))['total'] or 0
    revenue_30 = paid_orders.filter(created_at__gte=last_30).aggregate(total=Sum('total'))['total'] or 0

    # محصولات پرفروش
    top_products = (
        OrderItem.objects
        .filter(order__in=paid_orders)
        .values('product_name')
        .annotate(total_qty=Sum('quantity'), total_amount=Sum('total_price'))
        .order_by('-total_qty')[:5]
    )

    # نمودار فروش ۷ روز اخیر
    daily_sales = []
    for i in range(6, -1, -1):
        day = now.date() - timedelta(days=i)
        day_orders = paid_orders.filter(created_at__date=day)
        day_revenue = day_orders.aggregate(total=Sum('total'))['total'] or 0
        jalali_date = jdatetime.date.fromgregorian(date=day)
        daily_sales.append({
            'date': jalali_date.strftime('%m/%d'),
            'revenue': int(day_revenue),
        })

    # سفارش‌های اخیر
    recent_orders = all_orders.select_related('user')[:5]

    context = {
        'vendor': vendor,
        'total_orders': total_orders,
        'pending_orders': pending_orders,
        'paid_orders': paid_orders_count,
        'total_revenue': total_revenue,
        'total_revenue_all_time': total_revenue_all_time,
        'commission': int(commission),
        'net_payable': net_payable,
        'revenue_7': revenue_7,
        'revenue_30': revenue_30,
        'top_products': top_products,
        'daily_sales': daily_sales,
        'recent_orders': recent_orders,
    }
    return render(request, 'vendors/dashboard.html', context)


@vendor_required
def order_list(request):
    vendor = request.user.vendor
    status_filter = request.GET.get('status', '')

    orders = Order.objects.filter(vendor=vendor).select_related('user')
    if status_filter:
        orders = orders.filter(status=status_filter)

    context = {
        'orders': orders,
        'status_filter': status_filter,
        'status_choices': Order.STATUS_CHOICES,
    }
    return render(request, 'vendors/order_list.html', context)


@vendor_required
def order_detail(request, order_number):
    vendor = request.user.vendor
    order = get_object_or_404(Order, order_number=order_number, vendor=vendor)

    if request.method == 'POST':
        new_status = request.POST.get('status')
        tracking_code = request.POST.get('tracking_code', '').strip()

        if new_status in dict(Order.STATUS_CHOICES):
            old_status = order.status
            order.status = new_status
            if tracking_code:
                order.tracking_code = tracking_code
            order.save()

            # ← اعلان به مشتری
            if old_status != new_status:
                status_label_old = dict(Order.STATUS_CHOICES).get(old_status, old_status)
                status_label_new = dict(Order.STATUS_CHOICES).get(new_status, new_status)
                Notification.send(
                    user=order.user,
                    title=f"وضعیت سفارش {order.order_number} تغییر کرد",
                    message=f"وضعیت سفارش شما از «{status_label_old}» به «{status_label_new}» تغییر یافت."
                            + (f" کد رهگیری پست: {tracking_code}" if tracking_code else ""),
                    type='order_status',
                    link=f"/cart/order/{order.order_number}/",
                )

            messages.success(request, "وضعیت سفارش به‌روزرسانی شد.")
            return redirect('vendors:order_detail', order_number=order.order_number)
        else:
            messages.error(request, "وضعیت نامعتبر است.")

    context = {
        'order': order,
        'status_choices': Order.STATUS_CHOICES,
    }
    return render(request, 'vendors/order_detail.html', context)


@vendor_required
def settlements_list(request):
    """تاریخچه تسویه‌های فروشنده"""
    vendor = request.user.vendor
    settlements = VendorSettlement.objects.filter(vendor=vendor).order_by('-created_at')

    # آمار کل
    total_paid = settlements.filter(status='paid').aggregate(total=Sum('net_payable'))['total'] or 0
    pending_settlements = settlements.filter(status='draft')
    pending_total = pending_settlements.aggregate(total=Sum('net_payable'))['total'] or 0

    return render(request, 'vendors/settlements_list.html', {
        'settlements': settlements,
        'total_paid': total_paid,
        'pending_total': pending_total,
        'pending_count': pending_settlements.count(),
    })


@vendor_required
def coupon_list(request):
    vendor = request.user.vendor
    coupons = Coupon.objects.filter(vendor=vendor).order_by('-created_at')
    return render(request, 'vendors/coupon_list.html', {'coupons': coupons})


@vendor_required
def coupon_create(request):
    vendor = request.user.vendor

    if request.method == 'POST':
        code = request.POST.get('code', '').strip().upper()
        discount_type = request.POST.get('discount_type', 'percent')
        discount_value = request.POST.get('discount_value', '0')
        min_purchase = request.POST.get('min_purchase', '0') or '0'
        max_discount = request.POST.get('max_discount', '').strip()
        max_uses = request.POST.get('max_uses', '0') or '0'
        valid_from = request.POST.get('valid_from')
        valid_until = request.POST.get('valid_until')

        # اعتبارسنجی
        if not code or not valid_from or not valid_until:
            messages.error(request, "کد، تاریخ شروع و پایان الزامی است.")
            return render(request, 'vendors/coupon_form.html', {'mode': 'create'})

        if Coupon.objects.filter(vendor=vendor, code=code).exists():
            messages.error(request, "این کد قبلاً در فروشگاه شما ثبت شده است.")
            return render(request, 'vendors/coupon_form.html', {'mode': 'create'})

        try:
            Coupon.objects.create(
                vendor=vendor,
                code=code,
                discount_type=discount_type,
                discount_value=int(float(discount_value)),
                min_purchase=int(float(min_purchase)),
                max_discount=int(float(max_discount)) if max_discount else None,
                max_uses=int(max_uses),
                valid_from=valid_from,
                valid_until=valid_until,
            )
            messages.success(request, "کد تخفیف با موفقیت ایجاد شد.")
            return redirect('vendors:coupon_list')
        except (ValueError, TypeError) as e:
            messages.error(request, f"خطا در مقادیر وارد شده: {e}")

    return render(request, 'vendors/coupon_form.html', {'mode': 'create'})


@vendor_required
def coupon_toggle(request, coupon_id):
    if request.method != 'POST':
        return redirect('vendors:coupon_list')

    vendor = request.user.vendor
    coupon = get_object_or_404(Coupon, id=coupon_id, vendor=vendor)
    coupon.is_active = not coupon.is_active
    coupon.save()
    messages.success(request, "وضعیت کد تخفیف تغییر کرد.")
    return redirect('vendors:coupon_list')

