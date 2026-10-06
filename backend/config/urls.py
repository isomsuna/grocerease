from django.contrib import admin
from django.urls import path

from accounts.views import (
    CurrentUserView,
    LoginView,
    LogoutView,
    PasswordChangeView,
    PasswordResetConfirmView,
    PasswordResetRequestView,
    RegisterView,
    csrf_bootstrap,
)
from core.views import health

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/health', health, name='health'),
    path('api/health/', health),
    path('api/auth/csrf/', csrf_bootstrap, name='auth-csrf'),
    path('api/auth/register/', RegisterView.as_view(), name='auth-register'),
    path('api/auth/login/', LoginView.as_view(), name='auth-login'),
    path('api/auth/logout/', LogoutView.as_view(), name='auth-logout'),
    path(
        'api/auth/password-reset/',
        PasswordResetRequestView.as_view(),
        name='password-reset',
    ),
    path(
        'api/auth/password-reset/confirm/',
        PasswordResetConfirmView.as_view(),
        name='password-reset-confirm',
    ),
    path('api/auth/password-change/', PasswordChangeView.as_view(), name='password-change'),
    path('api/me/', CurrentUserView.as_view(), name='current-user'),
]
