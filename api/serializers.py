from rest_framework import serializers
from catalog.models import Product, Category, ProductImage
from vendors.models import Vendor
from orders.models import Cart, CartItem
from orders.models import Order, OrderItem, Coupon, CouponUsage


class VendorPublicSerializer(serializers.ModelSerializer):
    class Meta:
        model = Vendor
        fields = ['id', 'name', 'legal_name']


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'slug']


class ProductImageSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()

    class Meta:
        model = ProductImage
        fields = ['id', 'url', 'is_main', 'alt_text']

    def get_url(self, obj):
        request = self.context.get('request')
        if request and obj.image:
            return request.build_absolute_uri(obj.image.url)
        return obj.image.url if obj.image else None


class ProductListSerializer(serializers.ModelSerializer):
    vendor = VendorPublicSerializer(read_only=True)
    main_image = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = ['id', 'name', 'slug', 'price', 'stock', 'is_active',
                  'vendor', 'main_image']

    def get_main_image(self, obj):
        img = obj.main_image
        if not img:
            return None
        request = self.context.get('request')
        if request:
            return request.build_absolute_uri(img.image.url)
        return img.image.url


class ProductDetailSerializer(serializers.ModelSerializer):
    vendor = VendorPublicSerializer(read_only=True)
    category = CategorySerializer(read_only=True)
    images = ProductImageSerializer(many=True, read_only=True)

    class Meta:
        model = Product
        fields = ['id', 'name', 'slug', 'description', 'price', 'stock',
                  'is_active', 'vendor', 'category', 'images', 'created_at']


class CartItemSerializer(serializers.ModelSerializer):
    product = ProductListSerializer(read_only=True)
    product_id = serializers.IntegerField(write_only=True, required=False)
    subtotal = serializers.SerializerMethodField()

    class Meta:
        model = CartItem
        fields = ['id', 'product', 'product_id', 'quantity', 'subtotal']

    def get_subtotal(self, obj):
        return int(obj.product.price * obj.quantity)


class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    total_items = serializers.SerializerMethodField()
    total_price = serializers.SerializerMethodField()
    items_by_vendor = serializers.SerializerMethodField()

    class Meta:
        model = Cart
        fields = ['id', 'items', 'total_items', 'total_price', 'items_by_vendor']

    def get_total_items(self, obj):
        return obj.total_items

    def get_total_price(self, obj):
        return int(obj.total_price)

    def get_items_by_vendor(self, obj):
        result = {}
        for item in obj.items.select_related('product__vendor'):
            vendor_id = item.product.vendor.id
            vendor_name = item.product.vendor.name
            key = f"{vendor_id}:{vendor_name}"
            if key not in result:
                result[key] = {
                    'vendor_id': vendor_id,
                    'vendor_name': vendor_name,
                    'items': [],
                    'subtotal': 0,
                }
            result[key]['items'].append(CartItemSerializer(item).data)
            result[key]['subtotal'] += int(item.product.price * item.quantity)
        return list(result.values())

class CheckoutInputSerializer(serializers.Serializer):
    """اعتبارسنجی ورودی Checkout"""
    receiver_name = serializers.CharField(max_length=100)
    receiver_phone = serializers.CharField(max_length=15)
    shipping_province = serializers.CharField(max_length=50)
    shipping_city = serializers.CharField(max_length=50)
    shipping_postal_code = serializers.CharField(max_length=10)
    shipping_address = serializers.CharField()
    notes = serializers.CharField(required=False, allow_blank=True)
    coupon_code = serializers.CharField(required=False, allow_blank=True)


class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = ['id', 'product_name', 'unit_price', 'quantity', 'total_price']


class OrderListSerializer(serializers.ModelSerializer):
    vendor_name = serializers.CharField(source='vendor.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Order
        fields = ['id', 'order_number', 'vendor_name', 'total',
                  'discount_amount', 'status', 'status_display', 'created_at']


class OrderDetailSerializer(serializers.ModelSerializer):
    vendor_name = serializers.CharField(source='vendor.name', read_only=True)
    vendor_legal_name = serializers.CharField(source='vendor.legal_name', read_only=True)
    vendor_national_id = serializers.CharField(source='vendor.national_id', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    items = OrderItemSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = [
            'id', 'order_number', 'status', 'status_display',
            'vendor_name', 'vendor_legal_name', 'vendor_national_id',
            'receiver_name', 'receiver_phone',
            'shipping_province', 'shipping_city',
            'shipping_postal_code', 'shipping_address',
            'subtotal', 'discount_amount', 'shipping_cost', 'total',
            'payment_ref_id', 'paid_at', 'tracking_code',
            'notes', 'created_at', 'items',
        ]

