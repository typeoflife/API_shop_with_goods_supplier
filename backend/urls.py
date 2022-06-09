from django.urls import path
from django_rest_passwordreset.views import reset_password_request_token, reset_password_confirm
from rest_framework.routers import DefaultRouter

from backend.views import OrdersViewset, ContactViewset, BasketViewset, PartnerStateViewset, \
    PartnerOrdersViewset, PartnerUpdateViewset, ProductInfoViewset, ShopListViewset, CategoryListViewset, \
    LoginAccountViewset, AccountDetailsViewset, RegisterAccountViewset, ConfirmAccountViewset, PasswordResetCustom

router = DefaultRouter()
router.register('user/register', RegisterAccountViewset)
router.register('user/login', LoginAccountViewset)
router.register('user/password_reset', PasswordResetCustom)
router.register('user/confirm', ConfirmAccountViewset)
router.register('user/details', AccountDetailsViewset)
router.register('user/contact', ContactViewset)
router.register('products', ProductInfoViewset)
router.register('categories', CategoryListViewset)
router.register('shops', ShopListViewset)
router.register('orders', OrdersViewset)
router.register('basket', BasketViewset)
router.register('partner/update', PartnerUpdateViewset)
router.register('partner/state', PartnerStateViewset)
router.register('partner/orders', PartnerOrdersViewset)


app_name = 'backend'
urlpatterns = [

    path('user/password_reset/confirm', reset_password_confirm, name='password-reset-confirm'),

] + router.urls
