from distutils.util import strtobool

from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
from django.db import IntegrityError
from django.db.models import Q, Sum, F, Count
from django.http import JsonResponse
from django_rest_passwordreset.views import User
from requests import get
from rest_framework import viewsets
from rest_framework.authtoken.models import Token
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from ujson import loads as load_json
from yaml import load as load_yaml, Loader
from backend.models import Shop, Category, Product, ProductInfo, Parameter, ProductParameter, Order, OrderItem, \
    Contact, ConfirmEmailToken
from backend.permissions import IsOwner, ShopPermission
from backend.serializers import UserSerializer, CategorySerializer, ShopSerializer, ProductInfoSerializer, \
    OrderItemSerializer, OrderSerializer, ContactSerializer, OrdersSerializer, BasketSerializer, \
    PartnerOrdersSerializer, PartnerOrderSerializer
from backend.signals import new_user_registered, new_order

DELIVERY = 300


class RegisterAccountViewset(viewsets.ModelViewSet):
    """Viewset для регистрации покупателей"""

    queryset = User.objects.all()
    serializer_class = UserSerializer

    def create(self, request, *args, **kwargs):
        # проверяем обязательные аргументы
        if {'first_name', 'last_name', 'middle_name', 'email', 'password', 'company', 'position'}.issubset(
                request.data):
            errors = {}

            # проверяем пароль на сложность

            try:
                validate_password(request.data['password'])
            except Exception as password_error:
                error_array = []
                # noinspection PyTypeChecker
                for item in password_error:
                    error_array.append(item)
                return JsonResponse({'Status': False, 'Errors': {'password': error_array}})
            else:
                # проверяем данные для уникальности имени пользователя
                request.data._mutable = True
                request.data.update({})
                user_serializer = UserSerializer(data=request.data)
                if user_serializer.is_valid():
                    # сохраняем пользователя
                    user = user_serializer.save()
                    user.set_password(request.data['password'])
                    user.save()
                    new_user_registered.send(sender=self.__class__, user_id=user.id)
                    return JsonResponse({'Status': True})
                else:
                    return JsonResponse({'Status': False, 'Errors': user_serializer.errors})

        return JsonResponse({'Status': False, 'Errors': 'Не указаны все необходимые аргументы'})


class ConfirmAccountViewset(viewsets.ModelViewSet):
    """Viewset для подтверждения аккаунта"""

    queryset = User.objects.all()
    serializer_class = UserSerializer

    def create(self, request, *args, **kwargs):
        # проверяем обязательные аргументы
        if {'email', 'token'}.issubset(request.data):

            token = ConfirmEmailToken.objects.filter(user__email=request.data['email'],
                                                     key=request.data['token']).first()

            if token:
                token.user.is_active = True
                token.user.save()
                token.delete()
                return JsonResponse({'Status': True})
            else:
                return JsonResponse({'Status': False, 'Errors': 'Неправильно указан токен или email'})

        return JsonResponse({'Status': False, 'Errors': 'Не указаны все необходимые аргументы'})


class AccountDetailsViewset(viewsets.ModelViewSet):
    """Viewset для работы данными пользователя"""

    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return super().get_queryset().filter(id=self.request.user.id)

    # Редактирование методом create
    def create(self, request, *args, **kwargs):
        # проверяем обязательные аргументы
        if 'password' in request.data:
            errors = {}
            # проверяем пароль на сложность
            try:
                validate_password(request.data['password'])
            except Exception as password_error:
                error_array = []
                # noinspection PyTypeChecker
                for item in password_error:
                    error_array.append(item)
                return JsonResponse({'Status': False, 'Errors': {'password': error_array}})
            else:
                request.user.set_password(request.data['password'])

        # проверяем остальные данные
        user_serializer = UserSerializer(request.user, data=request.data, partial=True)
        if user_serializer.is_valid():
            user_serializer.save()
            return JsonResponse({'Status': True})
        else:
            return JsonResponse({'Status': False, 'Errors': user_serializer.errors})


class LoginAccountViewset(viewsets.ModelViewSet):
    """Viewset для авторизации пользователей"""

    queryset = User.objects.all()
    serializer_class = UserSerializer

    def create(self, request, *args, **kwargs):
        if {'email', 'password'}.issubset(request.data):
            user = authenticate(request, username=request.data['email'], password=request.data['password'])
            if user is not None:
                if user.is_active:
                    token, _ = Token.objects.get_or_create(user=user)
                    return JsonResponse({'Status': True, 'Token': token.key})

            return JsonResponse({'Status': False, 'Errors': 'Не верные логин|пароль, либо аккаунт не активирован'})

        return JsonResponse({'Status': False, 'Errors': 'Не указаны все необходимые аргументы'})


class CategoryListViewset(viewsets.ModelViewSet):
    """Viewset для просмотра категорий"""

    queryset = Category.objects.all()
    serializer_class = CategorySerializer


class ShopListViewset(viewsets.ModelViewSet):
    """Viewset для просмотра списка магазинов"""

    queryset = Shop.objects.all()
    serializer_class = ShopSerializer


class ProductInfoViewset(viewsets.ModelViewSet):
    """Viewset для поиска товаров"""

    queryset = ProductInfo.objects.all().order_by('id')
    serializer_class = ProductInfoSerializer

    def get_queryset(self):
        query = Q(shop__state=True)
        shop_id = self.request.query_params.get('shop_id')
        category_id = self.request.query_params.get('category_id')

        if shop_id:
            query = query & Q(shop_id=shop_id)

        if category_id:
            query = query & Q(product__category_id=category_id)

        return super().get_queryset().filter(
            query).select_related(
            'shop', 'product__category').prefetch_related(
            'product_parameters__parameter').distinct()


class BasketViewset(viewsets.ModelViewSet):
    """Viewset для корзины"""

    permission_classes = [IsAuthenticated, IsOwner]
    queryset = Order.objects.all().order_by('id')
    serializer_class = BasketSerializer

    def get_queryset(self):
        return super().get_queryset().filter(
            user_id=self.request.user.id, state='basket').annotate(
            sum=Sum(F('ordered_items__quantity') * F('ordered_items__product_info__price'))).annotate(
            delivery=Count('ordered_items__product_info__shop', distinct=True) * DELIVERY).annotate(
            total_sum=Sum(F('ordered_items__quantity') * F('ordered_items__product_info__price')) +
                      Count('ordered_items__product_info__shop', distinct=True) * DELIVERY)

    # добавить товары в корзину
    def create(self, request, *args, **kwargs):
        items_sting = request.data.get('items')
        if items_sting:
            try:
                items_dict = load_json(items_sting)
            except ValueError:
                return JsonResponse({'Status': False, 'Errors': 'Неверный формат запроса'})
            else:
                contact_id = Contact.objects.filter(user_id=request.user.id).values_list('pk', flat=True)[0]
                basket, _ = Order.objects.get_or_create(user_id=request.user.id, state='basket',
                                                        contact_id=contact_id)
                objects_created = 0
                for order_item in items_dict:
                    order_item.update({'order': basket.id})
                    serializer = OrderItemSerializer(data=order_item)
                    if serializer.is_valid():
                        try:
                            serializer.save()
                        except IntegrityError as error:
                            return JsonResponse({'Status': False, 'Errors': str(error)})
                        else:
                            objects_created += 1

                    else:
                        JsonResponse({'Status': False, 'Errors': serializer.errors})

                return JsonResponse({'Status': True, 'Создано объектов': objects_created})
        return JsonResponse({'Status': False, 'Errors': 'Не указаны все необходимые аргументы'})

    # удалить товары из корзины
    def delete(self, request, *args, **kwargs):
        items_sting = request.data.get('items')
        if items_sting:
            items_list = items_sting.split(',')
            basket, _ = Order.objects.get_or_create(user_id=request.user.id, state='basket')
            query = Q()
            objects_deleted = False
            for order_item_id in items_list:
                if order_item_id.isdigit():
                    query = query | Q(order_id=basket.id, id=order_item_id)
                    objects_deleted = True

            if objects_deleted:
                deleted_count = OrderItem.objects.filter(query).delete()[0]
                return JsonResponse({'Status': True, 'Удалено объектов': deleted_count})
        return JsonResponse({'Status': False, 'Errors': 'Не указаны все необходимые аргументы'})

    # редактировать товары в корзине
    def put(self, request, *args, **kwargs):
        items_sting = request.data.get('items')

        if items_sting:
            try:
                items_dict = load_json(items_sting)
            except ValueError:
                JsonResponse({'Status': False, 'Errors': 'Неверный формат запроса'})
            else:
                basket, _ = Order.objects.get_or_create(user_id=request.user.id, state='basket')
                objects_updated = 0
                for order_item in items_dict:
                    if type(order_item['id']) == int and type(order_item['quantity']) == int:
                        objects_updated += OrderItem.objects.filter(order_id=basket.id, id=order_item['id']).update(
                            quantity=order_item['quantity'])

                return JsonResponse({'Status': True, 'Обновлено объектов': objects_updated})
        return JsonResponse({'Status': False, 'Errors': 'Не указаны все необходимые аргументы'})


class PartnerUpdateViewset(viewsets.ModelViewSet):
    """Viewset для обновления прайса"""

    permission_classes = [IsAuthenticated, IsOwner, ShopPermission]
    queryset = Shop.objects.all()
    serializer_class = ShopSerializer

    def create(self, request, *args, **kwargs):
        url = request.data.get('url')
        if url:
            validate_url = URLValidator()
            try:
                validate_url(url)
            except ValidationError as e:
                return JsonResponse({'Status': False, 'Error': str(e)})
            else:
                stream = get(url).content

                data = load_yaml(stream, Loader=Loader)
                shop, _ = Shop.objects.get_or_create(name=data['shop'], user_id=request.user.id,
                                                     url=request.data['url'])
                for category in data['categories']:
                    category_object, _ = Category.objects.get_or_create(id=category['id'], name=category['name'])
                    category_object.shops.add(shop.id)
                    category_object.save()
                ProductInfo.objects.filter(shop_id=shop.id).delete()
                for item in data['goods']:
                    product, _ = Product.objects.get_or_create(name=item['name'], category_id=item['category'])

                    product_info = ProductInfo.objects.create(product_id=product.id,
                                                              external_id=item['id'],
                                                              model=item['model'],
                                                              price=item['price'],
                                                              quantity=item['quantity'],
                                                              price_rrc=item['price_rrc'],
                                                              shop_id=shop.id)
                    for name, value in item['parameters'].items():
                        parameter_object, _ = Parameter.objects.get_or_create(name=name)
                        ProductParameter.objects.create(product_info_id=product_info.id,
                                                        parameter_id=parameter_object.id,
                                                        value=value)

                return JsonResponse({'Status': True})

        return JsonResponse({'Status': False, 'Errors': 'Не указаны все необходимые аргументы'})


class PartnerStateViewset(viewsets.ModelViewSet):
    """Viewset для работы со статусом поставщика"""

    permission_classes = [IsAuthenticated, IsOwner, ShopPermission]
    queryset = Shop.objects.all()
    serializer_class = ShopSerializer

    # изменить текущий статус
    def create(self, request, *args, **kwargs):
        state = request.data.get('state')
        if state:
            try:
                Shop.objects.filter(user_id=request.user.id).update(state=strtobool(state))
                return JsonResponse({'Status': True})
            except ValueError as error:
                return JsonResponse({'Status': False, 'Errors': str(error)})

        return JsonResponse({'Status': False, 'Errors': 'Не указаны все необходимые аргументы'})


class PartnerOrdersViewset(viewsets.ModelViewSet):
    """Viewset ля получения заказов поставщиками"""

    permission_classes = [IsAuthenticated, IsOwner, ShopPermission]
    queryset = Order.objects.all()
    serializer_class = PartnerOrdersSerializer

    def get_queryset(self):
        return super().get_queryset().filter(
            ordered_items__product_info__shop__user_id=self.request.user.id).exclude(state='basket').prefetch_related(
            'ordered_items__product_info__product__category',
            'ordered_items__product_info__product_parameters__parameter').annotate(
            total_sum=Sum(F('ordered_items__quantity') * F('ordered_items__product_info__price')))

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = PartnerOrderSerializer(instance)
        return Response(serializer.data)


class ContactViewset(viewsets.ModelViewSet):
    """Viewset для контактов"""

    permission_classes = [IsAuthenticated, IsOwner]
    queryset = Contact.objects.all()
    serializer_class = ContactSerializer

    def get_queryset(self):
        return super().get_queryset().filter(user_id=self.request.user.id)

    def create(self, request, *args, **kwargs):
        if not Contact.objects.filter(user_id=request.user.id):
            request.data._mutable = True
            request.data.update({'user': request.user.id})
            serializer = ContactSerializer(data=request.data)

            if serializer.is_valid():
                serializer.save()
                return JsonResponse({'Status': True})
            else:
                return JsonResponse({'Status': False, 'Errors': serializer.errors})

        return JsonResponse({'Status': False, 'Errors': 'Вы уже создавали контакты для своего аккауна'})

    def delete(self, request, *args, **kwargs):
        items_sting = request.data.get('items')
        if items_sting:
            items_list = items_sting.split(',')
            query = Q()
            objects_deleted = False
            for contact_id in items_list:
                if contact_id.isdigit():
                    query = query | Q(user_id=request.user.id, id=contact_id)
                    objects_deleted = True

            if objects_deleted:
                deleted_count = Contact.objects.filter(query).delete()[0]
                return JsonResponse({'Status': True, 'Удалено объектов': deleted_count})
        return JsonResponse({'Status': False, 'Errors': 'Не указаны все необходимые аргументы'})

    def put(self, request, *args, **kwargs):
        if 'id' in request.data:
            if request.data['id'].isdigit():
                contact = Contact.objects.filter(id=request.data['id'], user_id=request.user.id).first()
                if contact:
                    serializer = ContactSerializer(contact, data=request.data, partial=True)
                    if serializer.is_valid():
                        serializer.save()
                        return JsonResponse({'Status': True})
                    else:
                        JsonResponse({'Status': False, 'Errors': serializer.errors})

        return JsonResponse({'Status': False, 'Errors': 'Не указаны все необходимые аргументы'})


class OrdersViewset(viewsets.ModelViewSet):
    """Viewset для заказов. В queryset фильтруем по ользователю, добавляем общую сумму с учетом доставки"""

    permission_classes = [IsAuthenticated, IsOwner]
    queryset = Order.objects.all().order_by('id')
    serializer_class = OrdersSerializer

    def get_queryset(self):
        return super().get_queryset().filter(user=self.request.user).exclude(state='basket').prefetch_related(
            'ordered_items__product_info__product__category',
            'ordered_items__product_info__product_parameters__parameter').annotate(
            total_sum=Sum(F('ordered_items__quantity') * F('ordered_items__product_info__price')) +
                      Count('ordered_items__product_info__shop', distinct=True) * DELIVERY).distinct()

    def create(self, request, *args, **kwargs):
        try:
            is_updated = Order.objects.filter(
                user_id=request.user.id, id=request.data['id']).update(
                contact_id=request.data['contact'],
                state='new')

        except IntegrityError as error:
            return JsonResponse({'Status': False, 'Errors': 'Неправильно указаны аргументы'})
        else:
            if is_updated:
                new_order.send(sender=self.__class__, user_id=request.user.id)
                return JsonResponse({'Status': True})

        return JsonResponse({'Status': False, 'Errors': 'Не указаны все необходимые аргументы'})

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = OrderSerializer(instance)
        return Response(serializer.data)
