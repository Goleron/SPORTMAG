"""
Сериализаторы пользователей и ролей для DRF API.
"""
from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from .models import User, Role


class RoleSerializer(serializers.ModelSerializer):
    """Сериализатор для роли"""
    
    class Meta:
        model = Role
        fields = ('id', 'name', 'description', 'created_at', 'updated_at')
        read_only_fields = ('id', 'created_at', 'updated_at')


class UserRegistrationSerializer(serializers.Serializer):
    """Сериализатор для регистрации пользователя"""
    username = serializers.CharField(max_length=100, min_length=3)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, validators=[validate_password])
    role_name = serializers.CharField(default='Buyer', required=False)
    
    def validate_username(self, value):
        """Проверка уникальности username"""
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("Пользователь с таким именем уже существует")
        return value
    
    def validate_email(self, value):
        """Проверка уникальности email"""
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Пользователь с таким email уже существует")
        return value


class UserSerializer(serializers.ModelSerializer):
    """Сериализатор для пользователя"""
    role = RoleSerializer(read_only=True)
    role_id = serializers.IntegerField(write_only=True, required=False)
    password = serializers.CharField(write_only=True, required=False, min_length=6)
    saved_cards = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = (
            'id', 'username', 'email', 'password', 'role', 'role_id',
            'is_active', 'last_login', 'settings', 'saved_cards',
            'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'created_at', 'updated_at', 'last_login', 'saved_cards')
    
    def get_saved_cards(self, obj):
        """Получить сохраненные карты (без полных данных, только маскированные)"""
        from apps.common.card_utils import mask_card_number
        cards = obj.get_saved_cards()
        masked_cards = []
        for card in cards:
            masked_card = {
                'last_four': card.get('last_four', '****'),
                'cardholder_name': card.get('cardholder_name', ''),
                'added_at': card.get('added_at', ''),
                'masked_number': mask_card_number(card.get('last_four', '****') if len(card.get('last_four', '')) == 4 else '****')
            }
            masked_cards.append(masked_card)
        
        return masked_cards
    
    def update(self, instance, validated_data):
        """Обновление пользователя (включая смену пароля через crypt в БД)."""
        role_id = validated_data.pop('role_id', None)
        if role_id is not None:
            try:
                role = Role.objects.get(id=role_id)
                instance.role = role
            except Role.DoesNotExist:
                raise serializers.ValidationError({'role_id': 'Роль не найдена'})
        
        new_password = validated_data.pop('password', None)
        if new_password:
            from .services import UserService
            UserService.update_password(instance.id, new_password)
        
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        update_fields = list(validated_data.keys())
        if role_id is not None:
            update_fields.append('role_id')
        if update_fields:
            instance.save(update_fields=update_fields)
        return instance


class UserListSerializer(serializers.ModelSerializer):
    """Упрощенный сериализатор для списка пользователей"""
    role_name = serializers.CharField(source='role.name', read_only=True)
    
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'role_name', 'is_active', 'created_at')
        read_only_fields = fields

