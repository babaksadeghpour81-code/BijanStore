from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from catalog.models import Product, Category
from catalog.forms import ProductForm    # ← پایین‌تر می‌سازیم
from .decorators import vendor_required
from catalog.models import Product, Category, ProductImage
from catalog.forms import ProductForm, ProductImageForm


@vendor_required
def product_list(request):
    vendor = request.user.vendor
    products = Product.objects.filter(vendor=vendor)
    return render(request, 'vendors/product_list.html', {'products': products})


@vendor_required
def product_create(request):
    vendor = request.user.vendor

    if request.method == 'POST':
        form = ProductForm(request.POST, vendor=vendor)
        if form.is_valid():
            product = form.save(commit=False)
            product.vendor = vendor
            product.save()
            messages.success(request, "محصول با موفقیت اضافه شد.")
            return redirect('vendors:product_list')
    else:
        form = ProductForm(vendor=vendor)

    return render(request, 'vendors/product_form.html', {'form': form, 'mode': 'create'})


@vendor_required
def product_edit(request, pk):
    vendor = request.user.vendor
    product = get_object_or_404(Product, pk=pk, vendor=vendor)

    if request.method == 'POST':
        form = ProductForm(request.POST, instance=product, vendor=vendor)
        if form.is_valid():
            form.save()
            messages.success(request, "محصول به‌روزرسانی شد.")
            return redirect('vendors:product_list')
    else:
        form = ProductForm(instance=product, vendor=vendor)

    return render(request, 'vendors/product_form.html', {
        'form': form, 'mode': 'edit', 'product': product
    })


@vendor_required
def product_delete(request, pk):
    vendor = request.user.vendor
    product = get_object_or_404(Product, pk=pk, vendor=vendor)

    if request.method == 'POST':
        product.delete()
        messages.info(request, "محصول حذف شد.")
        return redirect('vendors:product_list')

    return render(request, 'vendors/product_confirm_delete.html', {'product': product})

@vendor_required
def product_images(request, pk):
    """مدیریت تصاویر یک محصول خاص"""
    vendor = request.user.vendor
    product = get_object_or_404(Product, pk=pk, vendor=vendor)

    if request.method == 'POST':
        form = ProductImageForm(request.POST, request.FILES)
        if form.is_valid():
            image = form.save(commit=False)
            image.product = product
            # اگر اولین تصویر محصوله، خودکار اصلی بشه
            if not product.images.exists():
                image.is_main = True
            image.save()
            messages.success(request, "تصویر با موفقیت اضافه شد.")
            return redirect('vendors:product_images', pk=product.pk)
    else:
        form = ProductImageForm()

    return render(request, 'vendors/product_images.html', {
        'product': product,
        'form': form,
        'images': product.images.all(),
    })


@vendor_required
def image_set_main(request, pk, image_id):
    """تنظیم یک تصویر به‌عنوان تصویر اصلی"""
    if request.method != 'POST':
        return redirect('vendors:product_images', pk=pk)

    vendor = request.user.vendor
    product = get_object_or_404(Product, pk=pk, vendor=vendor)
    image = get_object_or_404(ProductImage, pk=image_id, product=product)

    image.is_main = True
    image.save()   # save خودش بقیه رو غیرفعال می‌کنه

    messages.success(request, "تصویر اصلی تغییر کرد.")
    return redirect('vendors:product_images', pk=product.pk)


@vendor_required
def image_delete(request, pk, image_id):
    """حذف یک تصویر"""
    if request.method != 'POST':
        return redirect('vendors:product_images', pk=pk)

    vendor = request.user.vendor
    product = get_object_or_404(Product, pk=pk, vendor=vendor)
    image = get_object_or_404(ProductImage, pk=image_id, product=product)

    was_main = image.is_main
    image.delete()

    # اگر تصویر اصلی حذف شد، یکی دیگه رو اصلی کن
    if was_main:
        first = product.images.first()
        if first:
            first.is_main = True
            first.save()

    messages.info(request, "تصویر حذف شد.")
    return redirect('vendors:product_images', pk=product.pk)
