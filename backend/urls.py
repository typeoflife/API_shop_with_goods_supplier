from django.urls import path
from django_rest_passwordreset.views import reset_password_request_token, reset_password_confirm
from rest_framework.routers import DefaultRouter

from backend.views import RegisterAccount, LoginAccount, \
    AccountDetails, ConfirmAccount, OrdersViewset, ContactViewset, BasketViewset, PartnerStateViewset, \
    PartnerOrdersViewset, PartnerUpdateViewset, ProductInfoViewset, ShopListViewset, CategoryListViewset

router = DefaultRouter()
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

    path('user/register', RegisterAccount.as_view(), name='user-register'),
    path('user/register/confirm', ConfirmAccount.as_view(), name='user-register-confirm'),
    path('user/details', AccountDetails.as_view(), name='user-details'),
    path('user/login', LoginAccount.as_view(), name='user-login'),
    path('user/password_reset', reset_password_request_token, name='password-reset'),
    path('user/password_reset/confirm', reset_password_confirm, name='password-reset-confirm'),

] + router.urls
