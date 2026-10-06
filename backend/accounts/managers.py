from django.contrib.auth.base_user import BaseUserManager


class UserManager(BaseUserManager):
    use_in_migrations = True

    def get_by_natural_key(self, username):
        return self.get(email__iexact=username)

    async def aget_by_natural_key(self, username):
        return await self.aget(email__iexact=username)

    def _create_user(self, email, password, **extra_fields):
        if not email or not email.strip():
            raise ValueError('An email address is required.')

        display_name = extra_fields.get('display_name')
        if not display_name or not display_name.strip():
            raise ValueError('A display name is required.')
        extra_fields['display_name'] = display_name.strip()

        email = self.normalize_email(email).strip().lower()
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superusers must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superusers must have is_superuser=True.')

        return self._create_user(email, password, **extra_fields)
