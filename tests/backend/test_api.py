import pytest

from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient
from backend.models import User, Contact


@pytest.fixture
def client():
    return APIClient()


@pytest.fixture
def user():
    return User.objects.create_user(
        first_name='Maxim',
        last_name='Petrov',
        middle_name='Denisovich',
        password='12345678Q',
        email='wehor73348@eoscast.com',
        company='MTS',
        position='logist',
        is_active=1,
        type='buyer'
    )


@pytest.fixture
def user_shop():
    return User.objects.create_user(
        first_name='Ivan',
        last_name='Petrov',
        middle_name='Semenovich',
        password='12345678W',
        email='ali@eoscast.com',
        company='Ali',
        position='director',
        is_active=1,
        type='shop'
    )


@pytest.fixture
def client_token(user):
    token, _ = Token.objects.get_or_create(user=user)
    return APIClient(HTTP_AUTHORIZATION='Token ' + token.key)


@pytest.fixture
def client_token_shop(user_shop):
    token, _ = Token.objects.get_or_create(user=user_shop)
    return APIClient(HTTP_AUTHORIZATION='Token ' + token.key)


@pytest.fixture
def contacts(user):
    return Contact.objects.create(
        user_id=user.id, city='Moscow', street='Gogolya',
        house='58', structure='1', building='5',
        apartment='73', phone='+79424238142')


@pytest.fixture
def update_pricelist(client_token_shop):
    return client_token_shop.post('/api/v1/partner/update/', data={
        'url': 'https://raw.githubusercontent.com/typeoflife/my_diplom/main/shop.yaml'})


@pytest.mark.django_db
def test_user_login(user, client):
    response = client.post('/api/v1/user/login/', data={'email': user.email, 'password': '12345678Q'})
    print(response.json())
    assert response.json()['Status'] == True


@pytest.mark.django_db
def test_get_user_details(user, client_token):
    response = client_token.get(f'/api/v1/user/details/{user.id}/')
    data = response.json()
    assert data['id'] == user.id and data['last_name'] == user.last_name


@pytest.mark.django_db
def test_user_password_reset(user, client):
    response = client.post('/api/v1/user/password_reset', data={'email': user.email})
    data = response.json()
    assert data['status'] == 'OK'


@pytest.mark.django_db
def test_create_and_get_contacts(user, client_token, contacts):
    contact_id = Contact.objects.filter(user_id=user.id).values_list('pk', flat=True)[0]
    response = client_token.get(f'/api/v1/user/contact/{contact_id}/')
    data = response.json()
    contact = Contact.objects.filter(user_id=user).values()[0]
    contact.pop('user_id')
    assert data == contact


@pytest.mark.django_db
def test_change_contacts(user, client_token, contacts):
    old_contacts = Contact.objects.filter(user_id=user).values()[0]
    contact_id = Contact.objects.filter(user_id=user.id).values_list('pk', flat=True)[0]
    data = {"city": "Piterburg", "street": "Mira", "house": "58", "structure": "4", "building": "76",
            "apartment": "13", "id": str(contact_id), "phone": "+79424902341"}
    client_token.put('/api/v1/user/contact/', data=data)
    assert old_contacts['city'] != data['city'] and old_contacts['phone'] != data['phone']


@pytest.mark.django_db
def test_price_update(client_token_shop):
    response = client_token_shop.post('/api/v1/partner/update/', data={
        'url': 'https://raw.githubusercontent.com/typeoflife/my_diplom/main/shop.yaml'})
    data = response.json()
    assert data['Status'] == True


@pytest.mark.django_db
def test_partner_state(client_token_shop, update_pricelist):
    response = client_token_shop.get('/api/v1/partner/state/')
    data = response.json()
    for info in data['results']:
        assert info['state'] == True


@pytest.mark.django_db
def test_partner_state_update(client_token_shop, update_pricelist):
    response = client_token_shop.post('/api/v1/partner/state/', data={'state': 'off'})
    data = response.json()
    assert data['Status'] == True


@pytest.mark.django_db
def test_shop_list(client, update_pricelist):
    response = client.get('/api/v1/shops/')
    data = response.json()
    assert data['count'] > 0


@pytest.mark.django_db
def test_find_product(client, update_pricelist):
    response = client.get('/api/v1/products/', data={"shop_id": "1", "category_id": "225"})
    data = response.json()
    assert len(data) > 0


@pytest.mark.django_db
def test_find_categories(client, update_pricelist):
    response = client.get('/api/v1/categories/')
    data = response.json()
    assert len(data) > 0


@pytest.mark.django_db
def test_get_basket(client_token, update_pricelist):
    response = client_token.get('/api/v1/basket/')
    data = response.json()
    assert len(data['results']) == 0


@pytest.mark.django_db
def test_get_product_in_basket(client_token, update_pricelist, contacts):
    data = {'items': ['[{"product_info": "2", "quantity": "2"},'
                      '{"product_info": "3", "quantity": "2"}]']}
    client_token.post('/api/v1/basket/', data)
    response = client_token.get('/api/v1/basket/')
    data = response.json()
    assert data['count'] == 1


@pytest.mark.django_db
def test_change_product_in_basket(client_token, update_pricelist, contacts):
    data = {'items': ['[{"product_info": "2", "quantity": "2"},'
                      '{"product_info": "3", "quantity": "2"}]']}
    client_token.post('/api/v1/basket/', data)
    response = client_token.put('/api/v1/basket/', {'items': ['[{"id":  2,"quantity": 4}]']})
    data = response.json()
    assert data['Status'] == True


@pytest.mark.django_db
def test_get_order(client_token, update_pricelist):
    response = client_token.get('/api/v1/orders/1/')
    data = response.json()
    assert data['detail'] == 'Not found.'


@pytest.mark.django_db
def test_get_orders(client_token, update_pricelist):
    response = client_token.get('/api/v1/orders/')
    data = response.json()
    assert len(data['results']) == 0
