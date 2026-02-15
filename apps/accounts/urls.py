"""
Маршруты приложения accounts: auth, roles, users.
"""
from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from . import views

app_name = 'accounts'

urlpatterns = [
    path('auth/register/', views.register_view, name='register'),
    path('auth/login/', views.login_view, name='login'),
    path('auth/logout/', views.logout_view, name='logout'),
    path('auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('auth/me/', views.me_view, name='me'),
    path('auth/password-reset/', views.password_reset_request, name='password-reset'),
    path('auth/password-reset-confirm/', views.password_reset_confirm, name='password-reset-confirm'),
    path('roles/', views.RoleListAPIView.as_view(), name='role-list'),
    path('roles/<int:pk>/', views.RoleDetailAPIView.as_view(), name='role-detail'),
    path('users/', views.UserListAPIView.as_view(), name='user-list'),
    path('users/<int:pk>/', views.UserDetailAPIView.as_view(), name='user-detail'),
    path('users/<int:pk>/orders/', views.UserOrdersAPIView.as_view(), name='user-orders'),
    path('users/me/settings/', views.user_settings_view, name='user-settings'),
]

