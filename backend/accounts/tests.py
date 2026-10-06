from django.contrib.auth import authenticate
from django.db import IntegrityError
from django.test import TestCase

from accounts.models import User


class UserIdentityTests(TestCase):
    def test_email_is_the_unique_login_identifier(self):
        self.assertEqual(User.USERNAME_FIELD, 'email')
        self.assertTrue(User._meta.get_field('email').unique)
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

    def test_superuser_can_be_created_with_email(self):
        user = User.objects.create_superuser(
            email='admin@example.com',
            password='safe-admin-password',
            display_name='Admin',
        )

        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)

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
