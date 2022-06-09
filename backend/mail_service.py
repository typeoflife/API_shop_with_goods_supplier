from django.core.mail import send_mail
from django_rest_passwordreset.models import ResetPasswordToken

from backend.celery import app
from backend.models import ConfirmEmailToken, User, Order


@app.task
def new_user_registered(user_email, user_id):
    # отправяем письмо при регистрации пользователя
    token, _ = ConfirmEmailToken.objects.get_or_create(user_id=user_id)
    send_mail(
        f"Activation token",
        f"{token.user} thanks for registration! \n{token.key}",
        'testflask@mail.ru',
        [user_email],
        fail_silently=False,
    )


@app.task
def password_reset_token_created(reset_password_token, user_email):
    # отправяем письмо для восстановления пароля
    send_mail(
        f"Token for reset",
        f"{reset_password_token}",
        'testflask@mail.ru',
        [user_email],
        fail_silently=False,
    )

@app.task
def new_order(user_id):
    # отправяем письмо при изменении статуса заказа
    user = User.objects.get(id=user_id)
    order = Order.objects.get(user_id=user_id)

    send_mail(
        f"Update order status",
        f"Hello {user}\nYour order №{order} has been created",
        'testflask@mail.ru',
        [user.email],
        fail_silently=False,
    )
