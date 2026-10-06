from django.contrib.auth import login, logout, update_session_auth_hash
from django.db import IntegrityError, transaction
from django.http import JsonResponse
from django.middleware.csrf import get_token
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie
from django.views.decorators.http import require_GET
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.serializers import (
    LoginSerializer,
    PasswordChangeSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    ProfileSerializer,
    RegistrationSerializer,
    SafeUserSerializer,
)
from accounts.services import (
    EmailAlreadyRegistered,
    authenticate_user,
    change_password,
    register_user,
    reset_password,
    send_password_reset,
)


@require_GET
@ensure_csrf_cookie
def csrf_bootstrap(request):
    get_token(request)
    response = JsonResponse({'detail': 'CSRF cookie set.'})
    response['Cache-Control'] = 'no-store'
    return response


@method_decorator(csrf_protect, name='dispatch')
class RegisterView(APIView):
    permission_classes = (AllowAny,)

    def post(self, request):
        serializer = RegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            user = register_user(**serializer.validated_data)
        except EmailAlreadyRegistered:
            return Response(
                {'email': ['An account with this email already exists.']},
                status=status.HTTP_400_BAD_REQUEST,
            )
        login(request, user)
        return Response(SafeUserSerializer(user).data, status=status.HTTP_201_CREATED)


@method_decorator(csrf_protect, name='dispatch')
class LoginView(APIView):
    permission_classes = (AllowAny,)
    throttle_scope = 'login'

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = authenticate_user(**serializer.validated_data)
        if user is None:
            return Response(
                {'detail': 'Unable to log in with the supplied credentials.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        login(request, user)
        return Response(SafeUserSerializer(user).data)


@method_decorator(csrf_protect, name='dispatch')
class LogoutView(APIView):
    permission_classes = (AllowAny,)

    def post(self, request):
        logout(request)
        return Response(status=status.HTTP_204_NO_CONTENT)


@method_decorator(csrf_protect, name='dispatch')
class PasswordResetRequestView(APIView):
    permission_classes = (AllowAny,)
    throttle_scope = 'password_reset'

    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        send_password_reset(email=serializer.validated_data['email'])
        return Response({'detail': 'If an account exists for that email, reset instructions have been sent.'})


@method_decorator(csrf_protect, name='dispatch')
class PasswordResetConfirmView(APIView):
    permission_classes = (AllowAny,)

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user, errors = reset_password(**serializer.validated_data)
        if user is None:
            return Response(
                {'detail': 'The reset link is invalid or expired.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if errors:
            return Response({'new_password': errors}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'detail': 'Password has been reset.'})


@method_decorator(csrf_protect, name='dispatch')
class PasswordChangeView(APIView):
    def post(self, request):
        serializer = PasswordChangeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        current_matches, errors = change_password(
            user=request.user,
            **serializer.validated_data,
        )
        if not current_matches:
            return Response(
                {'current_password': ['Current password is incorrect.']},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if errors:
            return Response({'new_password': errors}, status=status.HTTP_400_BAD_REQUEST)
        update_session_auth_hash(request, request.user)
        return Response({'detail': 'Password changed.'})


class CurrentUserView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        return Response(SafeUserSerializer(request.user).data)

    def patch(self, request):
        serializer = ProfileSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        try:
            with transaction.atomic():
                serializer.save()
        except IntegrityError:
            return Response(
                {'email': ['An account with this email already exists.']},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(SafeUserSerializer(request.user).data)
