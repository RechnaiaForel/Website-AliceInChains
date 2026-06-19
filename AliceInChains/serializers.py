from rest_framework import serializers

from .models import Cart, CartItem, Category, Manufacturer, Order, OrderItem, Product, Profile


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'parent']


class ManufacturerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Manufacturer
        fields = ['id', 'name', 'country', 'description']


class ProductSerializer(serializers.ModelSerializer):
    # Удобные read-only поля с человекочитаемыми названиями
    category_name = serializers.CharField(source='category.name', read_only=True)
    manufacturer_name = serializers.CharField(source='manufacturer.name', read_only=True)

    class Meta:
        model = Product
        fields = [
            'id', 'name', 'description', 'photo', 'price',
            'quantity_in_stock', 'category', 'category_name',
            'manufacturer', 'manufacturer_name',
        ]

    def validate_price(self, value):
        if value < 0:
            raise serializers.ValidationError("Цена не может быть отрицательной.")
        return value

    def validate_quantity_in_stock(self, value):
        if value < 0:
            raise serializers.ValidationError("Количество не может быть отрицательным.")
        return value


class CartItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    item_price = serializers.SerializerMethodField()

    class Meta:
        model = CartItem
        fields = ['id', 'cart', 'product', 'product_name', 'quantity', 'item_price']

    def get_item_price(self, obj):
        return obj.item_price()

    def validate(self, attrs):
        product = attrs.get('product', getattr(self.instance, 'product', None))
        quantity = attrs.get('quantity', getattr(self.instance, 'quantity', None))
        if product and quantity is not None and quantity > product.quantity_in_stock:
            raise serializers.ValidationError(
                f"Количество превышает доступное на складе ({product.quantity_in_stock} шт.)."
            )
        return attrs


class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(source='cartitem_set', many=True, read_only=True)
    total_price = serializers.SerializerMethodField()

    class Meta:
        model = Cart
        fields = ['id', 'user', 'created_at', 'items', 'total_price']
        read_only_fields = ['user', 'created_at']

    def get_total_price(self, obj):
        return obj.total_price()


class ProfileSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    email = serializers.EmailField(source='user.email', read_only=True)
    is_staff = serializers.BooleanField(source='user.is_staff', read_only=True)

    class Meta:
        model = Profile
        fields = ['username', 'email', 'is_staff', 'full_name', 'phone', 'address']


class OrderItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    item_price = serializers.SerializerMethodField()

    class Meta:
        model = OrderItem
        fields = ['id', 'product', 'product_name', 'quantity', 'price', 'item_price']

    def get_item_price(self, obj):
        return obj.item_price()


class OrderSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    items = OrderItemSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = ['id', 'username', 'created_at', 'delivery_address', 'total_price', 'items']
