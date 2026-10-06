from django.contrib.auth import get_user_model
from rest_framework import serializers

from accounts.services import password_validation_errors

User = get_user_model()


class SafeUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'display_name', 'email')
        read_only_fields = ('id', 'email')


class RegistrationSerializer(serializers.Serializer):
    display_name = serializers.CharField(max_length=150, trim_whitespace=True)
    email = serializers.EmailField(max_length=254, trim_whitespace=True)
    password = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate_email(self, value):
        value = value.strip().lower()
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError('An account with this email already exists.')
        return value

    def validate(self, attrs):
        candidate_user = User(
            email=attrs['email'],
            display_name=attrs['display_name'],
        )
        errors = password_validation_errors(attrs['password'], candidate_user)
        if errors:
            raise serializers.ValidationError({'password': errors})
        return attrs


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField(max_length=254, trim_whitespace=True)
    password = serializers.CharField(write_only=True, trim_whitespace=False)


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField(max_length=254, trim_whitespace=True)


class PasswordResetConfirmSerializer(serializers.Serializer):
    uid = serializers.CharField()
    token = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, trim_whitespace=False)


class PasswordChangeSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True, trim_whitespace=False)
    new_password = serializers.CharField(write_only=True, trim_whitespace=False)


class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'display_name', 'email')
        read_only_fields = ('id',)

    def validate_display_name(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError('This field may not be blank.')
        return value

    def validate_email(self, value):
        value = value.strip().lower()
        users = User.objects.filter(email__iexact=value).exclude(pk=self.instance.pk)
        if users.exists():
            raise serializers.ValidationError('An account with this email already exists.')
        return value
