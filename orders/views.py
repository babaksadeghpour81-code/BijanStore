import uuid
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.views.decorators.http import require_POST
from django.utils import timezone
from catalog.models import Product
from vendors.models import Vendor
from .forms import CheckoutForm
from .models import (
    Cart, CartItem, Order, OrderItem,
    Coupon, CouponUsage,
)
from .utils import get_or_create_cart
from notifications.models import Notification



def cart_detail(request):
    cart = get_or_create_cart(request)
    items_by_vendor = cart.items_by_vendor()
    return render(request, 'orders/cart.html', {
        'cart': cart,
        'items_by_vendor': items_by_vendor,
    })


@require_POST
def cart_add(request, product_id):
    cart = get_or_create_cart(request)
    product = get_object_or_404(Product, id=product_id, is_active=True)

    if product.stock <= 0:
        messages.error(request, "این محصول موجود نیست.")
        return redirect(request.META.get('HTTP_REFERER', 'catalog:home'))

    quantity = int(request.POST.get('quantity', 1))

    item, created = CartItem.objects.get_or_create(
        cart=cart, product=product,
        defaults={'quantity': quantity}
    )
    if not created:
        item.quantity += quantity
        if item.quantity > product.stock:
            item.quantity = product.stock
            messages.warning(request, f"حداکثر موجودی {product.name} {product.stock} عدد است.")
        item.save()

    messages.success(request, f"«{product.name}» به سبد خرید اضافه شد.")
    return redirect('orders:cart_detail')


@require_POST
def cart_update(request, item_id):
    cart = get_or_create_cart(request)
    item = get_object_or_404(CartItem, id=item_id, cart=cart)

    try:
        quantity = int(request.POST.get('quantity', 1))
    except ValueError:
        quantity = 1

    if quantity <= 0:
        item.delete()
        messages.info(request, "محصول از سبد خرید حذف شد.")
    else:
        if quantity > item.product.stock:
            quantity = item.product.stock
            messages.warning(request, f"حداکثر موجودی {item.product.name} {item.product.stock} عدد است.")
        item.quantity = quantity
        item.save()
        messages.success(request, "سبد خرید به‌روزرسانی شد.")

    return redirect('orders:cart_detail')


@require_POST
def cart_remove(request, item_id):
    cart = get_or_create_cart(request)
    item = get_object_or_404(CartItem, id=item_id, cart=cart)
    item.delete()
    messages.info(request, "محصول از سبد خرید حذف شد.")
    return redirect('orders:cart_detail')

@login_required
def checkout(request):
    """صفحه‌ی فرم اطلاعات ارسال"""
    cart = get_or_create_cart(request)

    if not cart.items.exists():
        messages.warning(request, "سبد خرید شما خالیه.")
        return redirect('orders:cart_detail')

    # پیش‌فرض‌ها از پروفایل کاربر
    initial = {
        'receiver_name': request.user.get_full_name() or request.user.username,
    }

    if request.method == 'POST':
        form = CheckoutForm(request.POST)
        if form.is_valid():
            # ذخیره اطلاعات در session و رفتن به صفحه پیش‌فاکتور
            request.session['checkout_data'] = form.cleaned_data
            return redirect('orders:checkout_review')
    else:
        form = CheckoutForm(initial=initial)

    return render(request, 'orders/checkout.html', {
        'form': form,
        'cart': cart,
    })


@login_required
def checkout_review(request):
    cart = get_or_create_cart(request)
    checkout_data = request.session.get('checkout_data')

    if not cart.items.exists() or not checkout_data:
        messages.warning(request, "لطفاً ابتدا اطلاعات ارسال را کامل کنید.")
        return redirect('orders:checkout')

    items_by_vendor = cart.items_by_vendor()

    # اعمال کد تخفیف اگر در session هست
    coupon_data = request.session.get('coupon_applied', {})  # {vendor_id: coupon_id}

    vendor_totals = {}
    vendor_discounts = {}
    grand_subtotal = 0
    grand_discount = 0

    for vendor, items in items_by_vendor.items():
        subtotal = sum(item.subtotal for item in items)
        vendor_totals[vendor] = subtotal
        grand_subtotal += subtotal

        discount = 0
        coupon_id = coupon_data.get(str(vendor.id))
        if coupon_id:
            coupon = Coupon.objects.filter(id=coupon_id, vendor=vendor).first()
            if coupon and coupon.is_valid:
                discount = coupon.calculate_discount(subtotal)
                # فقط اگه کاربر قبلاً ازش استفاده نکرده
                if CouponUsage.objects.filter(coupon=coupon, user=request.user).exists():
                    discount = 0
                else:
                    vendor_discounts[vendor] = coupon
        vendor_totals[vendor] -= discount
        grand_discount += discount

    grand_total = grand_subtotal - grand_discount

    # لیست کوپن‌های موجود هر فروشنده (برای نمایش در فرم)
    available_coupons = {}
    for vendor in items_by_vendor.keys():
        available_coupons[vendor] = Coupon.objects.filter(vendor=vendor, is_active=True)

    context = {
        'items_by_vendor': items_by_vendor,
        'vendor_totals': vendor_totals,
        'vendor_discounts': vendor_discounts,
        'available_coupons': available_coupons,
        'grand_subtotal': grand_subtotal,
        'grand_discount': grand_discount,
        'grand_total': grand_total,
        'checkout_data': checkout_data,
        'cart': cart,
    }
    return render(request, 'orders/checkout_review.html', context)


@login_required
@require_POST
def apply_coupon(request):
    """اعمال کد تخفیف در چک‌اوت"""
    code = request.POST.get('code', '').strip().upper()
    cart = get_or_create_cart(request)

    if not code:
        messages.error(request, "کد تخفیف را وارد کنید.")
        return redirect('orders:checkout_review')

    # جستجو در کوپن‌های فروشنده‌هایی که در سبد هستند
    vendor_ids = set(item.product.vendor_id for item in cart.items.all())
    coupon = Coupon.objects.filter(code=code, vendor_id__in=vendor_ids, is_active=True).first()

    if not coupon:
        messages.error(request, "کد تخفیف نامعتبر است.")
        return redirect('orders:checkout_review')

    if not coupon.is_valid:
        messages.error(request, "این کد منقضی شده یا به سقف استفاده رسیده است.")
        return redirect('orders:checkout_review')

    if CouponUsage.objects.filter(coupon=coupon, user=request.user).exists():
        messages.warning(request, "شما قبلاً از این کد استفاده کرده‌اید.")
        return redirect('orders:checkout_review')

    # اعتبارسنجی حداقل مبلغ برای همون فروشنده
    vendor_items = cart.items.filter(product__vendor=coupon.vendor)
    vendor_subtotal = sum(item.subtotal for item in vendor_items)
    if vendor_subtotal < coupon.min_purchase:
        messages.error(request, f"حداقل مبلغ خرید برای این کد {coupon.min_purchase} تومان است.")
        return redirect('orders:checkout_review')

    # ذخیره در session
    coupon_data = request.session.get('coupon_applied', {})
    coupon_data[str(coupon.vendor_id)] = coupon.id
    request.session['coupon_applied'] = coupon_data

    messages.success(request, f"کد تخفیف «{code}» اعمال شد.")
    return redirect('orders:checkout_review')


@login_required
@require_POST
def remove_coupon(request, vendor_id):
    coupon_data = request.session.get('coupon_applied', {})
    if str(vendor_id) in coupon_data:
        del coupon_data[str(vendor_id)]
        request.session['coupon_applied'] = coupon_data
    messages.info(request, "کد تخفیف حذف شد.")
    return redirect('orders:checkout_review')


@login_required
@transaction.atomic
def place_order(request):
    if request.method != 'POST':
        return redirect('orders:checkout')

    cart = get_or_create_cart(request)
    checkout_data = request.session.get('checkout_data')
    coupon_data = request.session.get('coupon_applied', {})

    if not cart.items.exists() or not checkout_data:
        messages.error(request, "اطلاعات سفارش نامعتبر است.")
        return redirect('orders:cart_detail')

    items_by_vendor = cart.items_by_vendor()
    created_orders = []

    for vendor, items in items_by_vendor.items():
        subtotal = sum(item.subtotal for item in items)
        discount = 0
        applied_coupon = None

        coupon_id = coupon_data.get(str(vendor.id))
        if coupon_id:
            coupon = Coupon.objects.filter(id=coupon_id, vendor=vendor).first()
            if coupon and coupon.is_valid:
                if not CouponUsage.objects.filter(coupon=coupon, user=request.user).exists():
                    discount = coupon.calculate_discount(subtotal)
                    applied_coupon = coupon

        final_total = subtotal - discount

        order = Order.objects.create(
            user=request.user,
            vendor=vendor,
            order_number=f"BS-{uuid.uuid4().hex[:8].upper()}",
            receiver_name=checkout_data['receiver_name'],
            receiver_phone=checkout_data['receiver_phone'],
            shipping_province=checkout_data['shipping_province'],
            shipping_city=checkout_data['shipping_city'],
            shipping_postal_code=checkout_data['shipping_postal_code'],
            shipping_address=checkout_data['shipping_address'],
            notes=checkout_data.get('notes', ''),
            subtotal=subtotal,
            shipping_cost=0,
            total=final_total,
            discount_amount=discount,
            coupon=applied_coupon,
            status='pending',
        )

        for item in items:
            OrderItem.objects.create(
                order=order,
                product=item.product,
                product_name=item.product.name,
                unit_price=item.product.price,
                quantity=item.quantity,
                total_price=item.subtotal,
            )
            item.product.stock -= item.quantity
            item.product.save()

        # ثبت استفاده از کوپن
        if applied_coupon:
            CouponUsage.objects.create(
                coupon=applied_coupon,
                user=request.user,
                order=order,
            )
            applied_coupon.used_count += 1
            applied_coupon.save()

        if vendor.owner:
            Notification.send(
                user=vendor.owner,
                title=f"سفارش جدید {order.order_number}",
                message=f"یک سفارش جدید به مبلغ {order.total} تومان ثبت شد. برای مشاهده به پنل فروشنده بروید.",
                type='order_status',
                link=f"/vendor/orders/{order.order_number}/",
            )

        created_orders.append(order)

    cart.delete()
    request.session.pop('checkout_data', None)
    request.session.pop('coupon_applied', None)
    Notification.send(
        user=request.user,
        title=f"{len(created_orders)} سفارش شما ثبت شد",
        message="سفارش شما با موفقیت ثبت شد و در انتظار پرداخت است. برای تکمیل خرید به صفحه سفارش‌های من بروید.",
        type='order_status',
        link='/cart/my-orders/',
    )
    messages.success(request, f"{len(created_orders)} سفارش با موفقیت ثبت شد.")
    return redirect('orders:order_success')


@login_required
def order_success(request):
    """صفحه‌ی موفقیت — بعد از ثبت سفارش‌ها"""
    return render(request, 'orders/order_success.html')


@login_required
def my_orders(request):
    """لیست سفارش‌های کاربر"""
    orders = Order.objects.filter(user=request.user).select_related('vendor')
    return render(request, 'orders/my_orders.html', {'orders': orders})


@login_required
def order_detail(request, order_number):
    """جزئیات یک سفارش"""
    order = get_object_or_404(Order, order_number=order_number, user=request.user)
    return render(request, 'orders/order_detail.html', {'order': order})

@login_required
@require_POST
def order_delete(request, order_number):
    """حذف سفارش توسط مشتری — فقط در حالت‌های مجاز"""
    order = get_object_or_404(Order, order_number=order_number, user=request.user)

    # فقط pending یا cancelled قابل حذف هستند
    if order.status not in ['pending', 'cancelled']:
        messages.error(request, "فقط سفارش‌های در انتظار پرداخت یا لغو‌شده قابل حذف هستند.")
        return redirect('orders:order_detail', order_number=order.order_number)

    with transaction.atomic():
        # اگر کوپن استفاده شده، آزادش کن
        if order.coupon:
            CouponUsage.objects.filter(coupon=order.coupon, order=order).delete()
            if order.coupon.used_count > 0:
                order.coupon.used_count -= 1
                order.coupon.save()

        order_number_saved = order.order_number
        order.delete()

    messages.success(request, f"سفارش {order_number_saved} با موفقیت حذف شد.")
    return redirect('orders:my_orders')