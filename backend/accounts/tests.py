from asgiref.sync import sync_to_async
from django.contrib.auth import aauthenticate, authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase

from accounts.models import User


class UserIdentityTests(TestCase):
    def test_email_is_the_unique_login_identifier(self):
        self.assertEqual(User.USERNAME_FIELD, 'email')
        self.assertTrue(
            any(
                constraint.name == 'accounts_user_email_ci_uniq'
                for constraint in User._meta.constraints
            )
        )
        self.assertNotIn('username', {field.name for field in User._meta.fields})

    def test_user_can_be_created_with_email_without_username(self):
        user = User.objects.create_user(
            email='alex@example.com',
            password='safe-test-password',
            display_name='Alex',
        )

        self.assertEqual(user.email, 'alex@example.com')
        self.assertEqual(user.display_name, 'Alex')
        self.assertTrue(user.check_password('safe-test-password'))
        self.assertEqual(
            authenticate(email='alex@example.com', password='safe-test-password'),
            user,
        )

    def test_email_is_normalized_and_login_is_case_insensitive(self):
        user = User.objects.create_user(
            email='Alex@GMAIL.com',
            password='safe-test-password',
            display_name='Alex',
        )

        self.assertEqual(user.email, 'alex@gmail.com')
        self.assertEqual(
            authenticate(email='ALEX@gmail.com', password='safe-test-password'),
            user,
        )

    async def test_async_email_login_is_case_insensitive(self):
        user = await sync_to_async(User.objects.create_user)(
            email='alex@example.com',
            password='safe-test-password',
            display_name='Alex',
        )

        self.assertEqual(
            await aauthenticate(email='ALEX@example.com', password='safe-test-password'),
            user,
        )

    def test_superuser_can_be_created_with_email(self):
        user = User.objects.create_superuser(
            email='admin@example.com',
            password='safe-admin-password',
            display_name='Admin',
        )

        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)

    def test_display_name_is_required_when_creating_a_user(self):
        with self.assertRaisesMessage(ValueError, 'A display name is required.'):
            User.objects.create_user(email='alex@example.com', password='safe-test-password')

        with self.assertRaisesMessage(ValueError, 'A display name is required.'):
            User.objects.create_user(
                email='alex@example.com',
                password='safe-test-password',
                display_name='  ',
            )

    def test_display_name_is_the_users_only_name_field(self):
        user = User.objects.create_user(
            email='alex@example.com',
            password='safe-test-password',
            display_name='Alex Example',
        )

        self.assertNotIn('first_name', {field.name for field in User._meta.fields})
        self.assertNotIn('last_name', {field.name for field in User._meta.fields})
        self.assertEqual(user.get_full_name(), 'Alex Example')
        self.assertEqual(user.get_short_name(), 'Alex Example')

    def test_password_similarity_validator_checks_display_name(self):
        user = User(email='alex@example.com', display_name='Alexandria')

        with self.assertRaises(ValidationError):
            validate_password('Alexandria123', user)

    def test_duplicate_email_cannot_be_created(self):
        User.objects.create_user(
            email='alex@example.com',
            password='safe-test-password',
            display_name='Alex',
        )

        with self.assertRaises(IntegrityError):
            User.objects.create_user(
                email='alex@example.com',
                password='another-test-password',
                display_name='Another Alex',
            )

    def test_email_uniqueness_ignores_case(self):
        User.objects.create_user(
            email='Alex@example.com',
            password='safe-test-password',
            display_name='Alex',
        )

        with self.assertRaises(IntegrityError):
            User.objects.create_user(
                email='alex@EXAMPLE.com',
                password='another-test-password',
                display_name='Another Alex',
            )
