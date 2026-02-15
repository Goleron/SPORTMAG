"""
Сервис регистрации, аутентификации и смены пароля (интеграция с БД).
"""
from django.db import connection
from django.contrib.auth import get_user_model
from .models import Role
from ..common.utils import set_current_user_id

User = get_user_model()


class UserService:
    """Сервис для работы с пользователями"""
    
    @staticmethod
    def register_user(username, email, password, role_name='Buyer'):
        """
        Регистрация пользователя через функцию БД register_user
        
        Args:
            username: имя пользователя
            email: email
            password: пароль (будет захеширован в БД)
            role_name: название роли (по умолчанию 'Buyer')
        
        Returns:
            user_id: ID созданного пользователя
        
        Raises:
            ValueError: если роль не найдена или пользователь уже существует
        """
        try:
            role = Role.objects.get(name=role_name)
        except Role.DoesNotExist:
            raise ValueError(f'Роль {role_name} не найдена')
        
        if User.objects.filter(username=username).exists():
            raise ValueError('Пользователь с таким именем уже существует')
        
        if User.objects.filter(email=email).exists():
            raise ValueError('Пользователь с таким email уже существует')
        
        with connection.cursor() as cursor:
            cursor.callproc('register_user', [username, email, password, role_name])
            result = cursor.fetchone()
            user_id = result[0] if result else None
        
        if not user_id:
            raise ValueError('Ошибка при создании пользователя')
        user = User.objects.get(id=user_id)
        return user
    
    @staticmethod
    def authenticate_user(username, password):
        """
        Аутентификация пользователя через функцию crypt БД
        
        Args:
            username: имя пользователя
            password: пароль
        
        Returns:
            User: объект пользователя или None
        """
        try:
            user = User.objects.get(username=username, is_active=True)
        except User.DoesNotExist:
            return None
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f'Ошибка при получении пользователя: {e}')
            return None
        
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT (password_hash = crypt(%s, password_hash)) FROM shop.users WHERE id = %s",
                    [password, user.id]
                )
                result = cursor.fetchone()
                
                if result and result[0]:
                    from django.utils import timezone
                    user.last_login = timezone.now()
                    user.save(update_fields=['last_login'])
                    return user
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f'Ошибка при проверке пароля: {e}')
            return None
        
        return None
    
    @staticmethod
    def set_user_context(user):
        """Установка контекста пользователя для триггеров БД"""
        if user:
            set_current_user_id(user.id)
            if user.role:
                from ..common.utils import set_current_role
                set_current_role(user.role.name)

    @staticmethod
    def update_password(user_id, new_password):
        """
        Обновить пароль пользователя (хеш через crypt в БД).
        Используется при смене пароля админом.
        """
        with connection.cursor() as cursor:
            cursor.execute(
                "UPDATE shop.users SET password_hash = crypt(%s, gen_salt('bf')) WHERE id = %s",
                [new_password, user_id]
            )
        return True

