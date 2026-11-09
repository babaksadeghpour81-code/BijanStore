from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.shortcuts import get_object_or_404

from catalog.models import Product, Category
from orders.models import Cart, CartItem
import uuid
from django.db import transaction
from django.utils import timezone
from orders.models import Order, OrderItem, Coupon, CouponUsage
from .serializers import (
    ProductListSerializer,
    ProductDetailSerializer,
    CategorySerializer,
    CartSerializer,
    CheckoutInputSerializer,
    OrderListSerializer,
    OrderDetailSerializer,
)
from notifications.models import Notification


def get_or_create_user_cart(user):
    """سبد خرید مخصوص API — بر اساس user (جدا از سبد وب)"""
    cart = Cart.objects.filter(user=user, session_key__isnull=True).first()
    if not cart:
        cart = Cart.objects.create(user=user)
    return cart


class ProductViewSet(viewsets.ReadOnlyModelViewSet):
    """API محصولات — فقط خواندن، عمومی"""
    queryset = Product.objects.filter(is_active=True).select_related('vendor', 'category')
    permission_classes = [AllowAny]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'description', 'vendor__name']
    ordering_fields = ['price', 'created_at', 'name']
    ordering = ['-created_at']

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return ProductDetailSerializer
        return ProductListSerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context


class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    """API دسته‌بندی‌ها"""
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [AllowAny]
    lookup_field = 'slug'


class CartViewSet(viewsets.ViewSet):
    """API سبد خرید — فقط برای کاربران لاگین‌کرده (JWT)"""
    permission_classes = [IsAuthenticated]

    def list(self, request):
        cart = get_or_create_user_cart(request.user)
        serializer = CartSerializer(cart, context={'request': request})
        return Response(serializer.data)

    @action(detail=False, methods=['post'], url_path='add')
    def add_item(self, request):
        product_id = request.data.get('product_id')
        try:
            quantity = int(request.data.get('quantity', 1))
        except (ValueError, TypeError):
            return Response({'error': 'تعداد نامعتبر است.'}, status=status.HTTP_400_BAD_REQUEST)

        if not product_id:
            return Response({'error': 'product_id الزامی است.'}, status=status.HTTP_400_BAD_REQUEST)

        product = get_object_or_404(Product, id=product_id, is_active=True)

        if product.stock <= 0:
            return Response({'error': 'این محصول موجود نیست.'}, status=status.HTTP_400_BAD_REQUEST)

        cart = get_or_create_user_cart(request.user)
        item, created = CartItem.objects.get_or_create(
            cart=cart, product=product,
            defaults={'quantity': quantity}
        )
        if not created:
            item.quantity += quantity
            if item.quantity > product.stock:
                item.quantity = product.stock
            item.save()

        serializer = CartSerializer(cart, context={'request': request})
        return Response(serializer.data)

    @action(detail=False, methods=['post'], url_path='update')
    def update_item(self, request):
        item_id = request.data.get('item_id')
        try:
            quantity = int(request.data.get('quantity', 1))
        except (ValueError, TypeError):
            return Response({'error': 'تعداد نامعتبر است.'}, status=status.HTTP_400_BAD_REQUEST)

        cart = get_or_create_user_cart(request.user)
        try:
            item = CartItem.objects.get(id=item_id, cart=cart)
        except CartItem.DoesNotExist:
            return Response({'error': 'قلم مورد نظر پیدا نشد.'}, status=status.HTTP_404_NOT_FOUND)

        if quantity <= 0:
            item.delete()
        else:
            if quantity > item.product.stock:
                quantity = item.product.stock
            item.quantity = quantity
            item.save()

        serializer = CartSerializer(cart, context={'request': request})
        return Response(serializer.data)

    @action(detail=False, methods=['post'], url_path='remove')
    def remove_item(self, request):
        item_id = request.data.get('item_id')

        cart = get_or_create_user_cart(request.user)
        try:
            item = CartItem.objects.get(id=item_id, cart=cart)
            item.delete()
        except CartItem.DoesNotExist:
            return Response({'error': 'قلم مورد نظر پیدا نشد.'}, status=status.HTTP_404_NOT_FOUND)

        serializer = CartSerializer(cart, context={'request': request})
        return Response(serializer.data)

class OrderViewSet(viewsets.ViewSet):
    """API سفارش‌ها — نیازمند JWT"""
    permission_classes = [IsAuthenticated]

    def list(self, request):
        """لیست سفارش‌های کاربر"""
        orders = Order.objects.filter(user=request.user).select_related('vendor').order_by('-created_at')
        serializer = OrderListSerializer(orders, many=True)
        return Response(serializer.data)

    def retrieve(self, request, pk=None):
        """جزئیات یک سفارش"""
        try:
            order = Order.objects.select_related('vendor').prefetch_related('items').get(
                order_number=pk, user=request.user
            )
        except Order.DoesNotExist:
            return Response({'error': 'سفارش پیدا نشد.'}, status=status.HTTP_404_NOT_FOUND)
        serializer = OrderDetailSerializer(order)
        return Response(serializer.data)

    @action(detail=False, methods=['post'], url_path='checkout')
    def checkout(self, request):
        """
        ایجاد سفارش از سبد خرید کاربر
        - برای هر فروشنده یک Order جدا ساخته می‌شه
        - کد تخفیف اعمال می‌شه (فقط به فروشنده مربوطه)
        - موجودی محصولات کاهش پیدا می‌کنه
        - سبد پاک می‌شه
        """
        input_serializer = CheckoutInputSerializer(data=request.data)
        if not input_serializer.is_valid():
            return Response(input_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = input_serializer.validated_data

        cart = Cart.objects.filter(user=request.user, session_key__isnull=True).first()
        if not cart or not cart.items.exists():
            return Response({'error': 'سبد خرید خالی است.'}, status=status.HTTP_400_BAD_REQUEST)

        items_by_vendor = cart.items_by_vendor()

        # اعتبارسنجی کوپن
        coupon_code = data.get('coupon_code', '').strip().upper()
        coupon = None
        if coupon_code:
            vendor_ids = [v.id for v in items_by_vendor.keys()]
            coupon = Coupon.objects.filter(
                code=coupon_code,
                vendor_id__in=vendor_ids,
                is_active=True,
            ).first()

            if not coupon:
                return Response({'error': 'کد تخفیف نامعتبر است.'}, status=status.HTTP_400_BAD_REQUEST)

            if not coupon.is_valid:
                return Response({'error': 'کد تخفیف منقضی شده یا به سقف استفاده رسیده است.'}, status=status.HTTP_400_BAD_REQUEST)

            if CouponUsage.objects.filter(coupon=coupon, user=request.user).exists():
                return Response({'error': 'شما قبلاً از این کد استفاده کرده‌اید.'}, status=status.HTTP_400_BAD_REQUEST)

            # بررسی حداقل مبلغ برای فروشنده کوپن
            vendor_items = cart.items.filter(product__vendor=coupon.vendor)
            vendor_subtotal = sum(item.product.price * item.quantity for item in vendor_items)
            if vendor_subtotal < coupon.min_purchase:
                return Response(
                    {'error': f'حداقل مبلغ خرید برای این کد {coupon.min_purchase} تومان است.'},
                    status=status.HTTP_400_BAD_REQUEST
                )

        created_orders = []

        with transaction.atomic():
            for vendor, items in items_by_vendor.items():
                subtotal = sum(item.product.price * item.quantity for item in items)
                discount = 0
                applied_coupon = None

                # اعمال کوپن فقط برای فروشنده مربوطه
                if coupon and coupon.vendor_id == vendor.id:
                    discount = coupon.calculate_discount(subtotal)
                    applied_coupon = coupon

                final_total = subtotal - discount

                order = Order.objects.create(
                    user=request.user,
                    vendor=vendor,
                    order_number=f"BS-{uuid.uuid4().hex[:8].upper()}",
                    receiver_name=data['receiver_name'],
                    receiver_phone=data['receiver_phone'],
                    shipping_province=data['shipping_province'],
                    shipping_city=data['shipping_city'],
                    shipping_postal_code=data['shipping_postal_code'],
                    shipping_address=data['shipping_address'],
                    notes=data.get('notes', ''),
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
                        total_price=item.product.price * item.quantity,
                    )
                    # کاهش موجودی
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

                created_orders.append(order)

            # پاک کردن سبد
            cart.delete()

        # اعلان به مشتری
        from notifications.models import Notification
        Notification.send(
            user=request.user,
            title=f"{len(created_orders)} سفارش شما ثبت شد",
            message="سفارش شما ثبت شد و در انتظار پرداخت است.",
            type='order_status',
            link='/cart/my-orders/',
            send_email=False,
        )

        # برگرداندن لیست سفارش‌های ساخته‌شده
        serializer = OrderListSerializer(created_orders, many=True)
        return Response({
            'message': f'{len(created_orders)} سفارش با موفقیت ثبت شد.',
            'orders': serializer.data,
        }, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], url_path='pay')
    def start_payment(self, request, pk=None):
        """
        شروع پرداخت برای یک سفارش
        - مرچنت کد از فروشنده گرفته می‌شه
        - لینک پرداخت زرین‌پال برگردونده می‌شه
        """
        try:
            order = Order.objects.select_related('vendor').get(
                order_number=pk, user=request.user
            )
        except Order.DoesNotExist:
            return Response({'error': 'سفارش پیدا نشد.'}, status=status.HTTP_404_NOT_FOUND)

        if order.status != 'pending':
            return Response({'error': 'این سفارش قابل پرداخت نیست.'}, status=status.HTTP_400_BAD_REQUEST)

        if not order.vendor.zarinpal_merchant_id:
            return Response({'error': 'فروشنده درگاه پرداخت را تنظیم نکرده است.'}, status=status.HTTP_400_BAD_REQUEST)

        from irgateway.zarinpal import ZarinpalClient
        from irgateway.zarinpal.enums import Environment
        from irgateway.zarinpal.errors import ZarinpalException
        from django.conf import settings

        env = Environment.SANDBOX if settings.ZARINPAL_SANDBOX else Environment.PRODUCTION
        client = ZarinpalClient(merchant_id=order.vendor.zarinpal_merchant_id, environment=env)

        # callback به API برمی‌گرده
        callback_url = f"{settings.ZARINPAL_CALLBACK_BASE}/api/v1/orders/payment-callback/{order.order_number}/"

        try:
            payment = client.request(
                amount=int(order.total) * 10,  # تومان → ریال
                callback_url=callback_url,
                description=f"پرداخت سفارش {order.order_number}",
            )
            order.payment_authority = payment.authority
            order.save()
            return Response({
                'payment_url': payment.payment_url,
                'authority': payment.authority,
            })
        except ZarinpalException as e:
            return Response({'error': f'خطا در اتصال به درگاه: {e.message}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['get'], url_path='payment-callback/(?P<order_number>[^/.]+)',
            permission_classes=[AllowAny], authentication_classes=[])
    def payment_callback(self, request, order_number=None):
        """
        کال‌بک زرین‌پال (بدون JWT — چون از درگاه برمی‌گرده)
        """
        try:
            order = Order.objects.select_related('vendor').get(order_number=order_number)
        except Order.DoesNotExist:
            return Response({'error': 'سفارش پیدا نشد.'}, status=status.HTTP_404_NOT_FOUND)

        authority = request.query_params.get('Authority')
        status_param = request.query_params.get('Status', 'NOK')

        if status_param != 'OK' or not authority:
            return Response({'error': 'پرداخت لغو شد یا ناموفق بود.'}, status=status.HTTP_400_BAD_REQUEST)

        from irgateway.zarinpal import ZarinpalClient
        from irgateway.zarinpal.enums import Environment
        from irgateway.zarinpal.errors import ZarinpalException
        from django.conf import settings

        env = Environment.SANDBOX if settings.ZARINPAL_SANDBOX else Environment.PRODUCTION
        client = ZarinpalClient(merchant_id=order.vendor.zarinpal_merchant_id, environment=env)

        try:
            verification = client.verify(
                authority=authority,
                amount=int(order.total) * 10,
            )
            if verification.code in [100, 101]:
                order.status = 'paid'
                order.payment_ref_id = str(verification.ref_id)
                order.paid_at = timezone.now()
                order.save()

                from notifications.models import Notification
                Notification.send(
                    user=order.user,
                    title=f"پرداخت سفارش {order.order_number} موفق بود",
                    message=f"پرداخت شما با کد رهگیری {verification.ref_id} ثبت شد.",
                    type='payment',
                    link=f"/cart/order/{order.order_number}/",
                    send_email=False,
                )

                return Response({
                    'status': 'success',
                    'ref_id': str(verification.ref_id),
                    'message': 'پرداخت با موفقیت انجام شد.',
                })
            else:
                return Response({'error': f'پرداخت تأیید نشد. کد: {verification.code}'}, status=status.HTTP_400_BAD_REQUEST)
        except ZarinpalException as e:
            return Response({'error': f'خطا در تأیید: {e.message}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['get'], url_path='status')
    def order_status(self, request, pk=None):
        """وضعیت یک سفارش — برای چک کردن نتیجه پرداخت"""
        try:
            order = Order.objects.get(order_number=pk, user=request.user)
        except Order.DoesNotExist:
            return Response({'error': 'سفارش پیدا نشد.'}, status=status.HTTP_404_NOT_FOUND)

        return Response({
            'order_number': order.order_number,
            'status': order.status,
            'status_display': order.get_status_display(),
            'payment_ref_id': order.payment_ref_id,
            'paid_at': order.paid_at.isoformat() if order.paid_at else None,
            'total': int(order.total),
        })

    @action(detail=True, methods=['post'], url_path='delete')
    def delete_order(self, request, pk=None):
        try:
            order = Order.objects.get(order_number=pk, user=request.user)
        except Order.DoesNotExist:
            return Response({'error': 'سفارش پیدا نشد.'}, status=status.HTTP_404_NOT_FOUND)

        if order.status not in ['pending', 'cancelled']:
            return Response(
                {'error': 'فقط سفارش‌های در انتظار پرداخت یا لغو‌شده قابل حذف هستند.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        with transaction.atomic():
            # برگرداندن موجودی محصولات
            for item in order.items.all():
                if item.product:
                    item.product.stock += item.quantity
                    item.product.save()

            # آزاد کردن کوپن
            if order.coupon:
                CouponUsage.objects.filter(coupon=order.coupon, order=order).delete()
                if order.coupon.used_count > 0:
                    order.coupon.used_count -= 1
                    order.coupon.save()

            order.delete()

        return Response({'status': 'ok', 'message': 'سفارش حذف شد.'})

class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    """API اعلان‌ها — فقط برای کاربر لاگین‌کرده"""
    permission_classes = [IsAuthenticated]
    serializer_class = None  # serializer inline

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user).order_by('-created_at')

    def list(self, request):
        notifications = self.get_queryset()
        data = []
        for n in notifications:
            data.append({
                'id': n.id,
                'type': n.type,
                'title': n.title,
                'message': n.message,
                'link': n.link,
                'is_read': n.is_read,
                'created_at': n.created_at.isoformat(),
            })
        return Response(data)

    @action(detail=True, methods=['post'], url_path='read')
    def mark_read(self, request, pk=None):
        try:
            notification = Notification.objects.get(id=pk, user=request.user)
        except Notification.DoesNotExist:
            return Response({'error': 'اعلان پیدا نشد.'}, status=status.HTTP_404_NOT_FOUND)
        notification.is_read = True
        notification.save()
        return Response({'status': 'ok'})

