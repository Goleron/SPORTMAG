"""
Эндпоинты аутентификации, пользователей, ролей и сброса пароля.
"""
from rest_framework import status, generics, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model
from .models import Role
from .serializers import (
    UserRegistrationSerializer,
    UserSerializer,
    UserListSerializer,
    RoleSerializer
)
from .services import UserService
from .email_service import send_registration_confirmation
from ..common.permissions import IsAdmin, IsOwnerOrAdmin

User = get_user_model()


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def register_view(request):
    """
    Регистрация нового пользователя
    
    POST /api/v1/auth/register/
    После успешной регистрации на email отправляется письмо с подтверждением.
    """
    serializer = UserRegistrationSerializer(data=request.data)
    if serializer.is_valid():
        try:
            user = UserService.register_user(
                username=serializer.validated_data['username'],
                email=serializer.validated_data['email'],
                password=serializer.validated_data['password'],
                role_name=serializer.validated_data.get('role_name', 'Buyer')
            )
            
            send_registration_confirmation(user.email, user.username)
            refresh = RefreshToken.for_user(user)
            
            return Response({
                'user_id': user.id,
                'username': user.username,
                'email': user.email,
                'role': user.role.name,
                'tokens': {
                    'refresh': str(refresh),
                    'access': str(refresh.access_token),
                }
            }, status=status.HTTP_201_CREATED)
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def login_view(request):
    """
    Вход в систему
    
    POST /api/v1/auth/login/
    """
    try:
        username = request.data.get('username')
        password = request.data.get('password')
        
        if not username or not password:
            return Response(
                {'error': 'Необходимо указать username и password'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        user = UserService.authenticate_user(username, password)
        
        if user:
            UserService.set_user_context(user)
            try:
                refresh = RefreshToken.for_user(user)
                
                return Response({
                    'user': UserSerializer(user).data,
                    'tokens': {
                        'refresh': str(refresh),
                        'access': str(refresh.access_token),
                    }
                }, status=status.HTTP_200_OK)
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f'Ошибка при генерации токенов: {e}')
                return Response(
                    {'error': 'Ошибка при создании токенов доступа'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        
        return Response(
            {'error': 'Неверные учетные данные'},
            status=status.HTTP_401_UNAUTHORIZED
        )
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f'Ошибка при входе: {e}')
        return Response(
            {'error': 'Внутренняя ошибка сервера'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def logout_view(request):
    """
    Выход из системы
    
    POST /api/v1/auth/logout/
    """
    try:
        refresh_token = request.data.get('refresh')
        if refresh_token:
            token = RefreshToken(refresh_token)
            token.blacklist()
    except Exception:
        pass
    
    return Response({'message': 'Успешный выход'}, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def me_view(request):
    """
    Получение информации о текущем пользователе
    
    GET /api/v1/auth/me/
    """
    serializer = UserSerializer(request.user)
    return Response(serializer.data)


class RoleListAPIView(generics.ListAPIView):
    """Список ролей"""
    queryset = Role.objects.all()
    serializer_class = RoleSerializer
    permission_classes = [permissions.IsAuthenticated]


class RoleDetailAPIView(generics.RetrieveAPIView):
    """Детали роли"""
    queryset = Role.objects.all()
    serializer_class = RoleSerializer
    permission_classes = [permissions.IsAuthenticated]


class UserListAPIView(generics.ListAPIView):
    """Список пользователей (только для администраторов)"""
    queryset = User.objects.select_related('role').all()
    serializer_class = UserListSerializer
    permission_classes = [IsAdmin]
    filterset_fields = ['role', 'is_active']
    search_fields = ['username', 'email']
    ordering_fields = ['created_at', 'username']
    ordering = ['-created_at']


class UserDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    """Детали, обновление и удаление пользователя"""
    queryset = User.objects.select_related('role').all()
    serializer_class = UserSerializer
    permission_classes = [IsAdmin | IsOwnerOrAdmin]
    
    def perform_destroy(self, instance):
        """Мягкое удаление - деактивация пользователя"""
        instance.is_active = False
        instance.save()


class UserOrdersAPIView(generics.ListAPIView):
    """Заказы пользователя"""
    permission_classes = [IsAdmin | IsOwnerOrAdmin]
    
    def get_queryset(self):
        user_id = self.kwargs['pk']
        if not self.request.user.role.name == 'Admin' and self.request.user.id != user_id:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied()
        from django.db import models
        return models.QuerySet.none()


@api_view(['GET', 'PUT'])
@permission_classes([permissions.IsAuthenticated])
def user_settings_view(request):
    """
    Получение и обновление настроек пользователя
    
    GET /api/v1/users/me/settings/ - получить настройки
    PUT /api/v1/users/me/settings/ - обновить настройки
    """
    user = request.user
    
    if request.method == 'GET':
        settings = user.get_settings()
        return Response(settings, status=status.HTTP_200_OK)
    
    elif request.method == 'PUT':
        new_settings = request.data
        allowed_keys = [
            'theme', 'date_format', 'number_format', 'page_size',
            'catalog_filters', 'analytics_filters', 'saved_filters'
        ]
        current_settings = user.get_settings()
        for key in allowed_keys:
            if key in new_settings:
                current_settings[key] = new_settings[key]
        user.settings = current_settings
        user.save(update_fields=['settings'])
        
        return Response(current_settings, status=status.HTTP_200_OK)


import secrets
from django.core.cache import cache
from .email_service import send_password_reset_email

PASSWORD_RESET_CACHE_PREFIX = 'pw_reset:'
PASSWORD_RESET_TIMEOUT = 86400


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def password_reset_request(request):
    """
    Запрос на сброс пароля. Отправляет на email ссылку для смены пароля.
    
    POST /api/v1/auth/password-reset/
    Body: { "email": "user@example.com" }
    """
    email = (request.data.get('email') or '').strip().lower()
    if not email:
        return Response(
            {'error': 'Укажите email'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        user = User.objects.get(email__iexact=email, is_active=True)
    except User.DoesNotExist:
        return Response(
            {'message': 'Если аккаунт с таким email существует, на него отправлена ссылка для сброса пароля.'},
            status=status.HTTP_200_OK
        )
    
    token = secrets.token_urlsafe(32)
    cache.set(PASSWORD_RESET_CACHE_PREFIX + token, user.id, timeout=PASSWORD_RESET_TIMEOUT)
    send_password_reset_email(user.email, user.username, token)
    
    return Response(
        {'message': 'Если аккаунт с таким email существует, на него отправлена ссылка для сброса пароля.'},
        status=status.HTTP_200_OK
    )


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def password_reset_confirm(request):
    """
    Установка нового пароля по токену из письма.
    
    POST /api/v1/auth/password-reset-confirm/
    Body: { "token": "...", "new_password": "newpass123" }
    """
    token = (request.data.get('token') or '').strip()
    new_password = request.data.get('new_password')
    
    if not token:
        return Response({'error': 'Укажите токен'}, status=status.HTTP_400_BAD_REQUEST)
    if not new_password or len(new_password) < 8:
        return Response(
            {'error': 'Пароль должен содержать минимум 8 символов'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    cache_key = PASSWORD_RESET_CACHE_PREFIX + token
    user_id = cache.get(cache_key)
    if not user_id:
        return Response(
            {'error': 'Ссылка недействительна или истекла. Запросите сброс пароля снова.'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        user = User.objects.get(id=user_id, is_active=True)
    except User.DoesNotExist:
        cache.delete(cache_key)
        return Response(
            {'error': 'Пользователь не найден.'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    UserService.update_password(user.id, new_password)
    cache.delete(cache_key)
    
    return Response({'message': 'Пароль успешно изменён. Теперь вы можете войти с новым паролем.'}, status=status.HTTP_200_OK)
