from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.db.models import Sum, Count, Q
from django.utils import timezone
from datetime import timedelta
from vendors.models import Vendor
from orders.models import Order, VendorSettlement
from datetime import datetime
from django.db import transaction
from notifications.models import Notification
from catalog.models import Product
from catalog.models import Category
from django import forms


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name', 'vendor', 'parent']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-input'}),
            'vendor': forms.Select(attrs={'class': 'form-input'}),
            'parent': forms.Select(attrs={'class': 'form-input'}),
        }

@staff_member_required
def category_list(request):
    """لیست دسته‌بندی‌ها"""
    categories = Category.objects.select_related('vendor', 'parent').order_by('vendor__name', 'name')
    return render(request, 'dashboard/category_list.html', {'categories': categories})


@staff_member_required
def category_create(request):
    """ایجاد دسته‌بندی جدید"""
    if request.method == 'POST':
        form = CategoryForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "دسته‌بندی با موفقیت ایجاد شد.")
            return redirect('dashboard:category_list')
    else:
        form = CategoryForm()

    return render(request, 'dashboard/category_form.html', {
        'form': form,
        'mode': 'create',
    })


@staff_member_required
def category_edit(request, category_id):
    """ویرایش دسته‌بندی"""
    category = get_object_or_404(Category, id=category_id)

    if request.method == 'POST':
        form = CategoryForm(request.POST, instance=category)
        if form.is_valid():
            form.save()
            messages.success(request, "دسته‌بندی به‌روزرسانی شد.")
            return redirect('dashboard:category_list')
    else:
        form = CategoryForm(instance=category)

    return render(request, 'dashboard/category_form.html', {
        'form': form,
        'mode': 'edit',
        'category': category,
    })


@staff_member_required
def category_delete(request, category_id):
    """حذف دسته‌بندی"""
    category = get_object_or_404(Category, id=category_id)

    if request.method == 'POST':
        # بررسی: آیا محصولی به این دسته وصل است؟
        product_count = category.product_set.count() if hasattr(category, 'product_set') else 0
        product_count = category.products.count()

        if product_count > 0:
            messages.error(
                request,
                f"این دسته‌بندی {product_count} محصول دارد و قابل حذف نیست. ابتدا محصولات را به دسته دیگری منتقل کنید."
            )
            return redirect('dashboard:category_list')

        # بررسی زیردسته‌ها
        if category.children.exists():
            messages.error(request, "این دسته‌بندی دارای زیردسته است. ابتدا زیردسته‌ها را حذف کنید.")
            return redirect('dashboard:category_list')

        name = category.name
        category.delete()
        messages.success(request, f"دسته‌بندی «{name}» حذف شد.")
        return redirect('dashboard:category_list')

    return render(request, 'dashboard/category_confirm_delete.html', {'category': category})


@staff_member_required
def admin_dashboard(request):
    """داشبورد اصلی ادمین"""
    # آمار کلی
    total_vendors = Vendor.objects.count()
    active_vendors = Vendor.objects.filter(is_active=True).count()
    pending_vendors = Vendor.objects.filter(is_active=False).count()

    total_orders = Order.objects.count()
    paid_orders = Order.objects.filter(status__in=['paid', 'processing', 'shipped', 'delivered'])
    total_revenue = paid_orders.aggregate(total=Sum('total'))['total'] or 0

    # کمیسیون کل (بر اساس درصد هر فروشنده)
    total_commission = 0
    for order in paid_orders.select_related('vendor'):
        if order.vendor.commission_rate:
            total_commission += float(order.total) * (float(order.vendor.commission_rate) / 100)

    # سفارش‌های اخیر
    recent_orders = Order.objects.select_related('vendor', 'user').order_by('-created_at')[:10]

    # فروشنده‌های در انتظار تأیید
    pending_vendor_list = Vendor.objects.filter(is_active=False).order_by('-created_at')[:5]

    # فروش ۳۰ روز اخیر
    last_30 = timezone.now() - timedelta(days=30)
    monthly_revenue = paid_orders.filter(created_at__gte=last_30).aggregate(total=Sum('total'))['total'] or 0

    context = {
        'total_vendors': total_vendors,
        'active_vendors': active_vendors,
        'pending_vendors': pending_vendors,
        'total_orders': total_orders,
        'total_revenue': total_revenue,
        'total_commission': int(total_commission),
        'monthly_revenue': monthly_revenue,
        'recent_orders': recent_orders,
        'pending_vendor_list': pending_vendor_list,
    }
    return render(request, 'dashboard/admin_dashboard.html', context)


@staff_member_required
def vendor_management(request):
    """مدیریت فروشنده‌ها"""
    vendors = Vendor.objects.select_related('owner').order_by('-created_at')
    return render(request, 'dashboard/vendor_management.html', {'vendors': vendors})


@staff_member_required
def vendor_approve(request, vendor_id):
    """تأیید یا رد فروشنده"""
    if request.method != 'POST':
        return redirect('dashboard:vendor_management')

    vendor = get_object_or_404(Vendor, id=vendor_id)
    action = request.POST.get('action')

    if action == 'approve':
        vendor.is_active = True
        vendor.save()
        if vendor.owner:
            Notification.send(
                user=vendor.owner,
                title="🎉 فروشگاه شما تأیید شد",
                message=f"فروشگاه «{vendor.name}» تأیید شد. از این پس می‌توانید محصولات خود را عرضه کنید و سفارش دریافت کنید.",
                type='vendor',
                link='/vendor/dashboard/',
            )
        messages.success(request, f"فروشنده «{vendor.name}» تأیید شد.")
    elif action == 'reject':
        vendor.is_active = False
        vendor.save()
        if vendor.owner:
            Notification.send(
                user=vendor.owner,
                title="فروشگاه شما غیرفعال شد",
                message=f"دسترسی فروشگاه «{vendor.name}» به دلایل بررسی، غیرفعال شده است. برای اطلاعات بیشتر با پشتیبانی تماس بگیرید.",
                type='vendor',
            )
        messages.warning(request, f"فروشنده «{vendor.name}» غیرفعال شد.")

    return redirect('dashboard:vendor_management')


@staff_member_required
def settlements(request):
    """لیست فروشنده‌ها با مبلغ قابل تسویه"""
    vendors = Vendor.objects.filter(is_active=True)
    settlement_data = []

    for vendor in vendors:
        # سفارش‌های paid که هنوز تسویه نشدن
        unsettled = Order.objects.filter(
            vendor=vendor,
            status__in=['paid', 'processing', 'shipped', 'delivered'],
            settled_at__isnull=True,
        )

        total_sales = unsettled.aggregate(total=Sum('total'))['total'] or 0
        commission = 0
        if vendor.commission_rate:
            commission = float(total_sales) * (float(vendor.commission_rate) / 100)

        settlement_data.append({
            'vendor': vendor,
            'unsettled_count': unsettled.count(),
            'total_sales': int(total_sales),
            'commission': int(commission),
            'net_payable': int(float(total_sales) - commission),
        })

    # تاریخچه تسویه‌ها
    history = VendorSettlement.objects.select_related('vendor', 'created_by').order_by('-created_at')[:20]

    return render(request, 'dashboard/settlements.html', {
        'settlements': settlement_data,
        'history': history,
    })


@staff_member_required
def settlement_create(request, vendor_id):
    """ایجاد تسویه برای یک فروشنده"""
    vendor = get_object_or_404(Vendor, id=vendor_id, is_active=True)

    if request.method == 'POST':
        period_start = request.POST.get('period_start')
        period_end = request.POST.get('period_end')
        notes = request.POST.get('notes', '').strip()

        if not period_start or not period_end:
            messages.error(request, "تاریخ شروع و پایان الزامی است.")
            return redirect('dashboard:settlements')

        try:
            start = datetime.strptime(period_start, '%Y-%m-%d').date()
            end = datetime.strptime(period_end, '%Y-%m-%d').date()
        except ValueError:
            messages.error(request, "فرمت تاریخ نامعتبر است.")
            return redirect('dashboard:settlements')

        if start > end:
            messages.error(request, "تاریخ شروع نمی‌تواند بعد از تاریخ پایان باشد.")
            return redirect('dashboard:settlements')

        # سفارش‌هایی که در این دوره و هنوز تسویه نشدن
        orders = Order.objects.filter(
            vendor=vendor,
            status__in=['paid', 'processing', 'shipped', 'delivered'],
            settled_at__isnull=True,
            created_at__date__gte=start,
            created_at__date__lte=end,
        )

        if not orders.exists():
            messages.warning(request, "سفارشی در این دوره برای تسویه پیدا نشد.")
            return redirect('dashboard:settlements')

        total_sales = orders.aggregate(total=Sum('total'))['total'] or 0
        commission = 0
        if vendor.commission_rate:
            commission = float(total_sales) * (float(vendor.commission_rate) / 100)
        net_payable = float(total_sales) - commission

        with transaction.atomic():
            settlement = VendorSettlement.objects.create(
                vendor=vendor,
                period_start=start,
                period_end=end,
                total_sales=int(total_sales),
                commission=int(commission),
                net_payable=int(net_payable),
                notes=notes,
                created_by=request.user,
                status='draft',
            )
            # علامت‌گذاری سفارش‌ها
            orders.update(settled_at=timezone.now())

        messages.success(request, f"تسویه‌ی «{vendor.name}» با مبلغ {int(net_payable)} تومان ثبت شد (پیش‌نویس).")
        return redirect('dashboard:settlements')

    return redirect('dashboard:settlements')


@staff_member_required
def settlement_mark_paid(request, settlement_id):
    """تأیید پرداخت یک تسویه"""
    if request.method != 'POST':
        return redirect('dashboard:settlements')

    settlement = get_object_or_404(VendorSettlement, id=settlement_id)
    reference_no = request.POST.get('reference_no', '').strip()

    if settlement.status != 'draft':
        messages.warning(request, "این تسویه قبلاً تعیین وضعیت شده است.")
        return redirect('dashboard:settlements')

    settlement.status = 'paid'
    settlement.reference_no = reference_no
    settlement.paid_at = timezone.now()
    settlement.save()
    Notification.send(
        user=settlement.vendor.owner,
        title="💰 تسویه پرداخت شد",
        message=f"تسویه دوره {settlement.period_start} تا {settlement.period_end} با مبلغ {settlement.net_payable} تومان پرداخت شد. شماره پیگیری: {reference_no or '—'}",
        type='settlement',
        link='/vendor/settlements/',
    )
    messages.success(request, f"پرداخت تسویه‌ی «{settlement.vendor.name}» ثبت شد.")
    return redirect('dashboard:settlements')


@staff_member_required
def settlement_cancel(request, settlement_id):
    """لغو تسویه و برگرداندن سفارش‌ها"""
    if request.method != 'POST':
        return redirect('dashboard:settlements')

    settlement = get_object_or_404(VendorSettlement, id=settlement_id)

    if settlement.status == 'paid':
        messages.error(request, "تسویه‌ی پرداخت‌شده قابل لغو نیست.")
        return redirect('dashboard:settlements')

    with transaction.atomic():
        # برگرداندن سفارش‌های این تسویه
        Order.objects.filter(
            vendor=settlement.vendor,
            created_at__date__gte=settlement.period_start,
            created_at__date__lte=settlement.period_end,
            settled_at__isnull=False,
        ).update(settled_at=None)
        settlement.status = 'cancelled'
        settlement.save()

    messages.info(request, "تسویه لغو شد و سفارش‌ها به حالت قابل تسویه برگشتند.")
    return redirect('dashboard:settlements')

