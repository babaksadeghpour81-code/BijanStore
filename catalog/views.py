from django.shortcuts import render, get_object_or_404
from django.db.models import Q
from .models import Product, Category
from vendors.models import Vendor


def home(request):
    """صفحه اصلی با جستجو و فیلتر"""
    products = Product.objects.filter(is_active=True).select_related('vendor', 'category')

    # جستجو
    q = request.GET.get('q', '').strip()
    if q:
        products = products.filter(
            Q(name__icontains=q) |
            Q(description__icontains=q) |
            Q(vendor__name__icontains=q)
        )

    # فیلتر دسته‌بندی
    category_slug = request.GET.get('category', '').strip()
    active_category = None
    if category_slug:
        active_category = Category.objects.filter(slug=category_slug).first()
        if active_category:
            category_ids = [active_category.id] + list(
                active_category.children.values_list('id', flat=True)
            )
            products = products.filter(category_id__in=category_ids)

    # فیلتر فروشنده
    vendor_slug = request.GET.get('vendor', '').strip()
    active_vendor = None
    if vendor_slug:
        active_vendor = Vendor.objects.filter(subdomain=vendor_slug, is_active=True).first()
        if active_vendor:
            products = products.filter(vendor=active_vendor)

    # مرتب‌سازی
    sort = request.GET.get('sort', 'newest')
    sort_map = {
        'newest': '-created_at',
        'cheapest': 'price',
        'expensive': '-price',
        'name': 'name',
    }
    products = products.order_by(sort_map.get(sort, '-created_at'))

    # لیست برای فیلتر
    categories = Category.objects.filter(
        products__is_active=True
    ).distinct().select_related('parent')

    vendors = Vendor.objects.filter(
        is_active=True, products__is_active=True
    ).distinct()

    context = {
        'products': products,
        'categories': categories,
        'vendors': vendors,
        'q': q,
        'active_category': active_category,
        'active_vendor': active_vendor,
        'sort': sort,
    }
    return render(request, 'catalog/home.html', context)


def product_detail(request, slug):
    """صفحه جزئیات محصول"""
    product = get_object_or_404(Product, slug=slug, is_active=True)
    related = Product.objects.filter(
        category=product.category, is_active=True
    ).exclude(id=product.id)[:4]

    return render(request, 'catalog/product_detail.html', {
        'product': product,
        'related': related,
    })

