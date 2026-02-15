"""
Отправка email: подтверждение регистрации и сброс пароля (SMTP).
"""
import logging
from django.core.mail import send_mail
from django.conf import settings

logger = logging.getLogger(__name__)


def send_registration_confirmation(email, username):
    """
    Отправить письмо с подтверждением регистрации.
    Не блокирует регистрацию при ошибке отправки (fail_silently=True).
    """
    subject = 'Подтверждение регистрации — СпортМаг'
    message = (
        f'Здравствуйте, {username}!\n\n'
        'Вы успешно зарегистрированы в интернет-магазине СпортМаг.\n\n'
        'Теперь вы можете войти в личный кабинет, оформлять заказы и отслеживать их статус.\n\n'
        'С уважением,\n'
        'Команда СпортМаг'
    )
    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            fail_silently=True,
        )
    except Exception as e:
        logger.warning('Не удалось отправить письмо подтверждения регистрации: %s', e)


def send_password_reset_email(email, username, reset_token):
    """
    Отправить письмо со ссылкой для сброса пароля.
    """
    frontend_url = getattr(settings, 'FRONTEND_URL', 'http://127.0.0.1:8001').rstrip('/')
    reset_link = f'{frontend_url}/reset-password/{reset_token}/'
    subject = 'Сброс пароля — СпортМаг'
    message = (
        f'Здравствуйте, {username}!\n\n'
        'Вы запросили сброс пароля для учётной записи в СпортМаг.\n\n'
        f'Перейдите по ссылке для установки нового пароля (действует 24 часа):\n{reset_link}\n\n'
        'Если вы не запрашивали сброс пароля, проигнорируйте это письмо.\n\n'
        'С уважением,\n'
        'Команда СпортМаг'
    )
    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            fail_silently=True,
        )
    except Exception as e:
        logger.warning('Не удалось отправить письмо сброса пароля: %s', e)
