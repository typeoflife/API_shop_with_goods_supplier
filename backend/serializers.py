# Верстальщик
from rest_framework import serializers

from backend.models import User, Category, Shop, ProductInfo, Product, ProductParameter, OrderItem, Order, Contact


class ContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contact
        fields = ('id', 'city', 'street', 'house', 'structure', 'building', 'apartment', 'user', 'phone')
        read_only_fields = ('id',)
        extra_kwargs = {
            'user': {'write_only': True}
        }


class UserSerializer(serializers.ModelSerializer):
    contacts = ContactSerializer(read_only=True, many=True)

    class Meta:
        model = User
        fields = ('id', 'first_name', 'last_name', 'middle_name', 'email', 'company', 'position', 'contacts')
        read_only_fields = ('id',)


class AdressSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contact
        fields = ('city', 'street', 'house', 'structure', 'building', 'apartment')
        read_only_fields = ('id',)


class PhoneSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contact
        fields = ('phone')
        read_only_fields = ('id',)


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ('id', 'name',)
        read_only_fields = ('id',)


class ShopSerializer(serializers.ModelSerializer):
    class Meta:
        model = Shop
        fields = ('id', 'name', 'state',)
        read_only_fields = ('id',)


class ProductSerializer(serializers.ModelSerializer):
    category = serializers.StringRelatedField()

    class Meta:
        model = Product
        fields = ('name', 'category',)


class ProductParameterSerializer(serializers.ModelSerializer):
    parameter = serializers.StringRelatedField()

    class Meta:
        model = ProductParameter
        fields = ('parameter', 'value',)


class ProductInfoSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)
    # product_parameters = ProductParameterSerializer(read_only=True, many=True)
    shop = serializers.StringRelatedField()

    class Meta:
        model = ProductInfo
        fields = ('id', 'model', 'shop', 'price', 'product',)
        read_only_fields = ('id',)


class UsersInfoSerializer(serializers.ModelSerializer):
    phone = ContactSerializer(read_only=True, many=True)

    class Meta:
        model = User
        fields = ('last_name', 'first_name', 'middle_name', 'email', 'phone')
        read_only_fields = ('id',)
        extra_kwargs = {
            'user': {'write_only': True}
        }


class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = ('id', 'product_info', 'quantity', 'order',)
        read_only_fields = ('id',)
        extra_kwargs = {
            'order': {'write_only': True}
        }


class OrderItemCreateSerializer(OrderItemSerializer):
    product_info = ProductInfoSerializer(read_only=True)


class OrderSerializer(serializers.ModelSerializer):
    ordered_items = OrderItemCreateSerializer(read_only=True, many=True)
    total_sum = serializers.IntegerField()
    user = UsersInfoSerializer(read_only=True)
    # phone = serializers.SlugRelatedField(read_only=True, slug_field='phone')
    contact = AdressSerializer(read_only=True)

    class Meta:
        model = Order
        fields = ('id', 'dt', 'state', 'ordered_items', 'total_sum', 'user', 'contact',)
        read_only_fields = ('id',)


class OrdersSerializer(serializers.ModelSerializer):
    total_sum = serializers.IntegerField()

    class Meta:
        model = Order
        fields = ('id', 'dt', 'total_sum', 'state', 'total_sum',)
        read_only_fields = ('id',)
