import json
import re
from datetime import timedelta
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

from asgiref.sync import sync_to_async
from django.contrib.auth import aauthenticate, authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.cache import cache
from django.core import mail
from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.core.management import call_command
from django.db import IntegrityError, transaction
from django.test import Client, SimpleTestCase, TestCase, override_settings
from django.utils import timezone
from rest_framework.exceptions import ValidationError as DRFValidationError

from accounts.models import PasswordResetEmailJob, User
from accounts.services import process_password_reset_email_jobs, register_user
from config.settings import validate_frontend_password_reset_url


class AuthenticationConfigurationTests(SimpleTestCase):
    def test_production_password_reset_url_must_use_https(self):
        with self.assertRaises(ImproperlyConfigured):
            validate_frontend_password_reset_url(
                'http://localhost:5173/reset-password', debug=False
            )

        self.assertEqual(
            validate_frontend_password_reset_url(
                'https://shopper.example/reset-password', debug=False
            ),
            'https://shopper.example/reset-password',
        )

    def test_proxy_and_csrf_origins_are_configurable_from_environment(self):
        from config.settings import (
            configured_num_proxies,
            default_email_backend,
            parse_csrf_trusted_origins,
            parse_num_proxies,
            parse_secure_proxy_ssl_header,
        )

        self.assertEqual(
            parse_secure_proxy_ssl_header('true'),
            ('HTTP_X_FORWARDED_PROTO', 'https'),
        )
        self.assertIsNone(parse_secure_proxy_ssl_header('false'))
        self.assertEqual(parse_num_proxies('2'), 2)
        self.assertEqual(configured_num_proxies(None, debug=True), 0)
        with self.assertRaises(ImproperlyConfigured):
            configured_num_proxies(None, debug=False)
        self.assertEqual(configured_num_proxies('2', debug=False), 2)
        with self.assertRaises(ImproperlyConfigured):
            parse_num_proxies('-1')
        self.assertEqual(
            parse_csrf_trusted_origins(' https://app.example, https://admin.example '),
            ['https://app.example', 'https://admin.example'],
        )
        self.assertEqual(
            default_email_backend(debug=True),
            'django.core.mail.backends.console.EmailBackend',
        )
        self.assertEqual(
            default_email_backend(debug=False),
            'django.core.mail.backends.smtp.EmailBackend',
        )

    @override_settings(SECURE_PROXY_SSL_HEADER=('HTTP_X_FORWARDED_PROTO', 'https'))
    def test_forwarded_https_header_marks_requests_secure(self):
        from django.test import RequestFactory

        request = RequestFactory().get('/', HTTP_X_FORWARDED_PROTO='https')

        self.assertTrue(request.is_secure())

    def test_auth_scopes_have_throttle_rates(self):
        from django.conf import settings

        self.assertIn('accounts.throttles.IPScopedRateThrottle', settings.REST_FRAMEWORK[
            'DEFAULT_THROTTLE_CLASSES'
        ])
        self.assertEqual(settings.REST_FRAMEWORK['DEFAULT_THROTTLE_RATES']['login'], '5/minute')
        self.assertEqual(settings.REST_FRAMEWORK['DEFAULT_THROTTLE_RATES']['password_reset'], '3/hour')
        self.assertEqual(settings.REST_FRAMEWORK['DEFAULT_THROTTLE_RATES']['registration'], '5/hour')
        self.assertEqual(
            settings.REST_FRAMEWORK['DEFAULT_THROTTLE_RATES']['sensitive_account_change'],
            '5/minute',
        )
        self.assertGreaterEqual(settings.REST_FRAMEWORK['NUM_PROXIES'], 0)
        self.assertEqual(settings.CACHES['default']['BACKEND'], 'django.core.cache.backends.db.DatabaseCache')
        self.assertEqual(settings.CACHES['default']['LOCATION'], 'grocerease_auth_throttle_cache')
        self.assertGreater(settings.EMAIL_TIMEOUT, 0)


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

    def test_model_save_normalizes_email_to_lowercase(self):
        user = User(email='Alex@GMAIL.com', display_name='Alex')
        user.set_password('safe-test-password')
        user.save()

        self.assertEqual(user.email, 'alex@gmail.com')
        self.assertEqual(User.objects.get(pk=user.pk).email, 'alex@gmail.com')

    def test_full_clean_normalizes_email_before_constraint_validation(self):
        user = User(email='Alex@Example.com', display_name='Alex')

        user.full_clean(exclude=('password',))

        self.assertEqual(user.email, 'alex@example.com')

    def test_database_rejects_mixed_case_email_written_without_model_save(self):
        user = User.objects.create_user(
            email='alex@example.com',
            password='safe-test-password',
            display_name='Alex',
        )

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                User.objects.filter(pk=user.pk).update(email='Alex@EXAMPLE.com')

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

    def test_email_case_insensitivity_uses_existing_lowercase_and_unique_constraints(self):
        constraint_names = {constraint.name for constraint in User._meta.constraints}
        self.assertIn('accounts_user_email_lowercase', constraint_names)
        self.assertNotIn('accounts_user_email_ci_uniq', constraint_names)


class AuthenticationApiTests(TestCase):
    password = 'swordfish-Harbor-732!'

    def setUp(self):
        self.client = Client(enforce_csrf_checks=True)
        cache.clear()

    def request_json(self, method, path, data=None, *, csrf=True):
        headers = {}
        if method.lower() != 'get' and csrf:
            self.client.get('/api/auth/csrf/')
            csrf_cookie = self.client.cookies.get('csrftoken')
            if csrf_cookie:
                headers['HTTP_X_CSRFTOKEN'] = csrf_cookie.value
        return getattr(self.client, method.lower())(
            path,
            data=json.dumps(data or {}),
            content_type='application/json',
            **headers,
        )

    def register(self, **overrides):
        data = {
            'display_name': 'Alex Shopper',
            'email': 'alex@example.com',
            'password': self.password,
        }
        data.update(overrides)
        return self.request_json('post', '/api/auth/register/', data)

    def test_csrf_bootstrap_sets_cookie_and_auth_mutation_rejects_missing_token(self):
        response = self.client.get('/api/auth/csrf/')

        self.assertEqual(response.status_code, 200)
        self.assertIn('csrftoken', response.cookies)
        response = self.client.post(
            '/api/auth/register/',
            data=json.dumps({
                'display_name': 'Alex Shopper',
                'email': 'alex@example.com',
                'password': self.password,
            }),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 403)
        self.assertFalse(User.objects.exists())

    @override_settings(
        SECURE_PROXY_SSL_HEADER=('HTTP_X_FORWARDED_PROTO', 'https'),
        CSRF_TRUSTED_ORIGINS=['https://testserver'],
    )
    def test_csrf_accepts_https_origin_through_trusted_proxy(self):
        self.client.get('/api/auth/csrf/', HTTP_X_FORWARDED_PROTO='https')
        csrf_token = self.client.cookies['csrftoken'].value

        response = self.client.post(
            '/api/auth/register/',
            data=json.dumps({
                'display_name': 'Alex Shopper',
                'email': 'alex@example.com',
                'password': self.password,
            }),
            content_type='application/json',
            HTTP_X_FORWARDED_PROTO='https',
            HTTP_ORIGIN='https://testserver',
            HTTP_X_CSRFTOKEN=csrf_token,
        )

        self.assertEqual(response.status_code, 201, response.content)
        self.assertTrue(User.objects.filter(email='alex@example.com').exists())

    def test_registration_normalizes_email_hashes_password_and_starts_session(self):
        response = self.register(email='  Alex@Example.COM  ')

        self.assertEqual(response.status_code, 201, response.content)
        user = User.objects.get()
        self.assertEqual(user.email, 'alex@example.com')
        self.assertTrue(user.check_password(self.password))
        self.assertNotEqual(user.password, self.password)
        self.assertIn('_auth_user_id', self.client.session)
        self.assertEqual(response.json(), {
            'id': user.pk,
            'display_name': 'Alex Shopper',
            'email': 'alex@example.com',
        })

    def test_registration_rejects_case_insensitive_duplicate_email(self):
        User.objects.create_user(
            email='alex@example.com', password=self.password, display_name='Alex'
        )

        response = self.register(email='ALEX@EXAMPLE.COM')

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {
            'email': ['Unable to create an account with the supplied details.'],
        })
        self.assertEqual(User.objects.count(), 1)

    def test_registration_does_not_translate_unrelated_integrity_errors(self):
        with patch('accounts.services.User.objects.create_user', side_effect=IntegrityError('database failure')):
            with self.assertRaises(IntegrityError):
                register_user(
                    email='alex@example.com', display_name='Alex', password=self.password
                )

    def test_registration_is_rate_limited(self):
        responses = [
            self.register(email=f'shopper-{index}@example.com')
            for index in range(6)
        ]

        self.assertTrue(all(response.status_code == 201 for response in responses[:5]))
        self.assertEqual(responses[5].status_code, 429)

    def test_registration_returns_validation_error_for_non_string_email(self):
        response = self.register(email=['alex@example.com'])

        self.assertEqual(response.status_code, 400)
        self.assertIn('email', response.json())
        self.assertFalse(User.objects.exists())

    def test_login_accepts_mixed_case_email_and_returns_only_safe_profile(self):
        user = User.objects.create_user(
            email='alex@example.com', password=self.password, display_name='Alex'
        )

        response = self.request_json('post', '/api/auth/login/', {
            'email': 'ALEX@EXAMPLE.COM', 'password': self.password,
        })

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {
            'id': user.pk, 'display_name': 'Alex', 'email': 'alex@example.com',
        })
        self.assertIn('_auth_user_id', self.client.session)
        self.assertNotIn('password', response.json())
        self.assertNotIn(user.password, response.content.decode())

    def test_login_failure_is_generic_for_unknown_email_and_wrong_password(self):
        User.objects.create_user(
            email='alex@example.com', password=self.password, display_name='Alex'
        )

        wrong_password = self.request_json('post', '/api/auth/login/', {
            'email': 'alex@example.com', 'password': 'incorrect-secret',
        })
        unknown_email = self.request_json('post', '/api/auth/login/', {
            'email': 'missing@example.com', 'password': 'incorrect-secret',
        })

        self.assertEqual(wrong_password.status_code, 400)
        self.assertEqual(unknown_email.status_code, 400)
        self.assertEqual(wrong_password.json(), unknown_email.json())
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_logout_invalidates_session(self):
        self.register()
        self.assertIn('_auth_user_id', self.client.session)

        response = self.request_json('post', '/api/auth/logout/')

        self.assertEqual(response.status_code, 204)
        self.assertNotIn('_auth_user_id', self.client.session)
        self.assertEqual(self.client.get('/api/me/').status_code, 401)

    def test_current_profile_get_and_patch_expose_only_safe_fields(self):
        self.register()
        response = self.client.get('/api/me/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(set(response.json()), {'id', 'display_name', 'email'})

        response = self.request_json('patch', '/api/me/', {
            'display_name': 'Alex Market', 'email': 'ALEX@EXAMPLE.NET',
            'current_password': self.password,
            'is_staff': True, 'password': 'attempted-mass-assignment',
        })

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['display_name'], 'Alex Market')
        self.assertEqual(response.json()['email'], 'alex@example.net')
        self.assertEqual(set(response.json()), {'id', 'display_name', 'email'})
        user = User.objects.get()
        self.assertFalse(user.is_staff)
        self.assertTrue(user.check_password(self.password))

    def test_current_profile_reads_are_not_limited_by_sensitive_action_throttle(self):
        self.register()

        responses = [self.client.get('/api/me/') for _ in range(6)]

        self.assertTrue(all(response.status_code == 200 for response in responses))

    def test_email_change_requires_current_password(self):
        self.register()

        response = self.request_json('patch', '/api/me/', {'email': 'new@example.com'})

        self.assertEqual(response.status_code, 400)
        self.assertIn('current_password', response.json())
        self.assertEqual(User.objects.get().email, 'alex@example.com')

    def test_email_change_rejects_incorrect_current_password(self):
        self.register()

        response = self.request_json('patch', '/api/me/', {
            'email': 'new@example.com', 'current_password': 'wrong-password',
        })

        self.assertEqual(response.status_code, 400)
        self.assertIn('current_password', response.json())
        self.assertEqual(User.objects.get().email, 'alex@example.com')

    def test_email_change_does_not_disclose_registered_email_before_password_check(self):
        self.register()
        User.objects.create_user(
            email='taken@example.com', password=self.password, display_name='Other'
        )

        for data in (
            {'email': 'taken@example.com'},
            {'email': 'taken@example.com', 'current_password': 'wrong-password'},
        ):
            response = self.request_json('patch', '/api/me/', data)
            self.assertEqual(response.status_code, 400)
            self.assertEqual(set(response.json()), {'current_password'})
            self.assertNotIn('already exists', response.content.decode().lower())

        response = self.request_json('patch', '/api/me/', {
            'email': 'taken@example.com', 'current_password': self.password,
        })
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {
            'email': ['Unable to change the email to the supplied address.'],
        })
        self.assertNotIn('already exists', response.content.decode().lower())
        self.assertEqual(User.objects.get(email='alex@example.com').email, 'alex@example.com')

    def test_email_change_uniqueness_race_uses_the_same_generic_error(self):
        self.register()
        User.objects.create_user(
            email='taken@example.com', password=self.password, display_name='Other'
        )

        with patch('accounts.serializers.ProfileSerializer.save', side_effect=IntegrityError):
            response = self.request_json('patch', '/api/me/', {
                'email': 'taken@example.com', 'current_password': self.password,
            })

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {
            'email': ['Unable to change the email to the supplied address.'],
        })

    def test_display_name_change_does_not_require_current_password(self):
        self.register()

        response = self.request_json('patch', '/api/me/', {'display_name': 'New Name'})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(User.objects.get().display_name, 'New Name')

    def test_email_change_uses_lowercase_normalization_not_casefold(self):
        from accounts.serializers import ProfileSerializer

        user = User.objects.create_user(
            email='a@straße.de', password=self.password, display_name='Alex'
        )
        serializer = ProfileSerializer(user, data={'email': 'a@STRASSE.de'}, partial=True)

        with self.assertRaises(DRFValidationError):
            serializer.validate({'email': 'a@STRASSE.de'})

    def test_registration_validates_password_only_once(self):
        from django.contrib.auth.password_validation import validate_password

        with patch('accounts.services.validate_password', wraps=validate_password) as validate:
            response = self.register()

        self.assertEqual(response.status_code, 201)
        self.assertEqual(validate.call_count, 1)

    def test_protected_profile_returns_401_without_authentication(self):
        response = self.client.get('/api/me/')

        self.assertEqual(response.status_code, 401)

    def test_database_cache_table_is_created_by_migration_not_a_fake_model(self):
        from django.db import connection

        self.assertIn('grocerease_auth_throttle_cache', connection.introspection.table_names())
        self.assertFalse(any(model.__name__ == 'AuthThrottleCacheEntry' for model in User._meta.apps.get_models()))

    def test_session_authenticated_profile_mutation_requires_csrf(self):
        self.register()
        response = self.client.patch(
            '/api/me/', data=json.dumps({'display_name': 'Changed'}),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(User.objects.get().display_name, 'Alex Shopper')


@override_settings(
    EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
    DEFAULT_FROM_EMAIL='noreply@example.com',
    FRONTEND_PASSWORD_RESET_URL='https://app.example/reset-password',
)
class PasswordLifecycleApiTests(AuthenticationApiTests):
    new_password = 'Harbor-Pebble-419!'

    def setUp(self):
        super().setUp()
        mail.outbox.clear()

    def deliver_queued_reset_emails(self):
        return process_password_reset_email_jobs(batch_size=10)

    def start_reset(self, email):
        response = self.request_json('post', '/api/auth/password-reset/', {'email': email})
        self.assertEqual(response.status_code, 200, response.content)
        return response

    def confirm_reset(self, uid, token, password=None):
        return self.request_json('post', '/api/auth/password-reset/confirm/', {
            'uid': uid,
            'token': token,
            'new_password': password or self.new_password,
        })

    def reset_uid_and_token(self):
        reset_url = re.search(r'https://app\.example/reset-password\?[^\s]+', mail.outbox[0].body)
        self.assertIsNotNone(reset_url)
        query = parse_qs(urlparse(reset_url.group(0)).query)
        return query['uid'][0], query['token'][0]

    def test_password_reset_acknowledgment_does_not_disclose_account_or_token(self):
        User.objects.create_user(
            email='alex@example.com', password=self.password, display_name='Alex'
        )

        known = self.start_reset('alex@example.com')
        unknown = self.start_reset('missing@example.com')
        self.assertEqual(PasswordResetEmailJob.objects.count(), 1)
        self.deliver_queued_reset_emails()

        self.assertEqual(known.status_code, 200)
        self.assertEqual(known.json(), unknown.json())
        self.assertNotIn('token', known.content.decode().lower())
        self.assertNotIn('uid', known.content.decode().lower())
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('alex@example.com', mail.outbox[0].to)

    def test_password_reset_email_is_queued_outside_the_request(self):
        User.objects.create_user(
            email='alex@example.com', password=self.password, display_name='Alex'
        )
        with patch('accounts.services.send_mail', return_value=1) as deliver:
            response = self.start_reset('alex@example.com')
            self.assertEqual(response.status_code, 200)
            deliver.assert_not_called()
            self.assertEqual(PasswordResetEmailJob.objects.count(), 1)
            self.deliver_queued_reset_emails()
            deliver.assert_called_once()


    @patch('accounts.services.send_mail', side_effect=OSError('SMTP unavailable'))
    def test_password_reset_keeps_generic_acknowledgment_when_delivery_fails(self, _send_mail):
        User.objects.create_user(
            email='alex@example.com', password=self.password, display_name='Alex'
        )

        known = self.start_reset('alex@example.com')
        with self.assertLogs('accounts.services', level='WARNING') as delivery_logs:
            self.deliver_queued_reset_emails()
        unknown = self.start_reset('missing@example.com')

        self.assertEqual(known.status_code, 200)
        self.assertEqual(known.json(), unknown.json())
        self.assertTrue(any('Password reset email delivery failed (' in entry for entry in delivery_logs.output))
        self.assertTrue(any('(OSError): SMTP unavailable' in entry for entry in delivery_logs.output))
        self.assertNotIn('token=', '\n'.join(delivery_logs.output))

    def test_password_reset_delivery_logs_do_not_include_reset_token(self):
        User.objects.create_user(
            email='alex@example.com', password=self.password, display_name='Alex'
        )
        self.start_reset('alex@example.com')

        def fail_with_token(*, message, **_kwargs):
            reset_url = re.search(r'https://app\.example/reset-password\?[^\s]+', message)
            token = parse_qs(urlparse(reset_url.group(0)).query)['token'][0]
            raise OSError(f'SMTP unavailable while sending token {token}')

        with patch(
            'accounts.services.send_mail',
            side_effect=fail_with_token,
        ), self.assertLogs('accounts.services', level='ERROR') as delivery_logs:
            self.deliver_queued_reset_emails()

        self.assertTrue(any('SMTP unavailable' in entry for entry in delivery_logs.output))
        self.assertNotRegex('\n'.join(delivery_logs.output), r'token [\w-]+')
        job = PasswordResetEmailJob.objects.get()
        self.assertEqual(job.status, PasswordResetEmailJob.Status.QUEUED)
        self.assertEqual(job.attempt_count, 1)

    def test_password_reset_jobs_deduplicate_and_store_no_token(self):
        User.objects.create_user(
            email='alex@example.com', password=self.password, display_name='Alex'
        )

        self.start_reset('alex@example.com')
        self.start_reset('alex@example.com')

        self.assertEqual(PasswordResetEmailJob.objects.count(), 1)
        self.assertFalse(any(
            field.name in {'token', 'reset_token', 'link', 'reset_link'}
            for field in PasswordResetEmailJob._meta.fields
        ))

    def test_password_reset_skips_accounts_with_unusable_passwords(self):
        user = User.objects.create_user(
            email='alex@example.com', password=self.password, display_name='Alex'
        )
        user.set_unusable_password()
        user.save(update_fields=('password',))

        response = self.start_reset('alex@example.com')

        self.assertEqual(response.status_code, 200)
        self.assertFalse(PasswordResetEmailJob.objects.exists())
        self.assertEqual(self.deliver_queued_reset_emails(), 0)
        self.assertEqual(len(mail.outbox), 0)

    def test_password_reset_delivery_discards_job_if_password_becomes_unusable(self):
        user = User.objects.create_user(
            email='alex@example.com', password=self.password, display_name='Alex'
        )
        PasswordResetEmailJob.objects.create(user=user)
        user.set_unusable_password()
        user.save(update_fields=('password',))

        self.assertEqual(self.deliver_queued_reset_emails(), 1)
        self.assertFalse(PasswordResetEmailJob.objects.exists())
        self.assertEqual(len(mail.outbox), 0)

    def test_reset_request_pulls_delayed_queued_email_job_forward(self):
        User.objects.create_user(
            email='alex@example.com', password=self.password, display_name='Alex'
        )
        self.start_reset('alex@example.com')
        job = PasswordResetEmailJob.objects.get()
        job.available_at = timezone.now() + timedelta(hours=1)
        job.save(update_fields=('available_at',))

        self.start_reset('alex@example.com')

        job.refresh_from_db()
        self.assertLessEqual(job.available_at, timezone.now())

    def test_password_change_removes_pending_reset_email_job(self):
        self.register()
        self.start_reset('alex@example.com')

        response = self.request_json('post', '/api/auth/password-change/', {
            'current_password': self.password, 'new_password': self.new_password,
        })

        self.assertEqual(response.status_code, 200)
        self.assertFalse(PasswordResetEmailJob.objects.exists())

    def test_password_reset_confirmation_removes_another_pending_reset_email_job(self):
        User.objects.create_user(
            email='alex@example.com', password=self.password, display_name='Alex'
        )
        self.start_reset('alex@example.com')
        self.deliver_queued_reset_emails()
        uid, token = self.reset_uid_and_token()
        self.start_reset('alex@example.com')

        response = self.confirm_reset(uid, token)

        self.assertEqual(response.status_code, 200)
        self.assertFalse(PasswordResetEmailJob.objects.exists())

    def test_password_reset_job_retries_after_transient_delivery_failure(self):
        User.objects.create_user(
            email='alex@example.com', password=self.password, display_name='Alex'
        )
        self.start_reset('alex@example.com')

        with patch('accounts.services.send_mail', side_effect=OSError('SMTP unavailable')):
            self.assertEqual(self.deliver_queued_reset_emails(), 1)

        job = PasswordResetEmailJob.objects.get()
        self.assertEqual(job.status, PasswordResetEmailJob.Status.QUEUED)
        self.assertEqual(job.attempt_count, 1)
        job.available_at = timezone.now() - timedelta(seconds=1)
        job.save(update_fields=('available_at',))

        self.assertEqual(self.deliver_queued_reset_emails(), 1)
        self.assertFalse(PasswordResetEmailJob.objects.exists())
        self.assertEqual(len(mail.outbox), 1)

    def test_password_reset_job_recovers_after_worker_restart(self):
        User.objects.create_user(
            email='alex@example.com', password=self.password, display_name='Alex'
        )
        self.start_reset('alex@example.com')
        PasswordResetEmailJob.objects.update(
            status=PasswordResetEmailJob.Status.PROCESSING,
            locked_at=timezone.now() - timedelta(minutes=10),
        )

        self.assertEqual(self.deliver_queued_reset_emails(), 1)
        self.assertFalse(PasswordResetEmailJob.objects.exists())
        self.assertEqual(len(mail.outbox), 1)

    def test_reset_email_worker_command_processes_one_batch(self):
        User.objects.create_user(
            email='alex@example.com', password=self.password, display_name='Alex'
        )
        self.start_reset('alex@example.com')

        call_command('send_password_reset_emails', '--once')

        self.assertFalse(PasswordResetEmailJob.objects.exists())
        self.assertEqual(len(mail.outbox), 1)

    def test_reset_email_worker_keeps_polling_after_unexpected_batch_error(self):
        with patch(
            'accounts.management.commands.send_password_reset_emails.process_password_reset_email_jobs',
            side_effect=[OSError('temporary storage issue'), 1, 0],
        ) as process, patch(
            'accounts.management.commands.send_password_reset_emails.time.sleep',
            side_effect=[None, KeyboardInterrupt],
        ) as sleep, self.assertLogs(
            'accounts.management.commands.send_password_reset_emails', level='ERROR'
        ) as worker_logs:
            with self.assertRaises(KeyboardInterrupt):
                call_command('send_password_reset_emails', '--poll-interval', '0.1')

        self.assertEqual(process.call_count, 3)
        self.assertEqual(sleep.call_count, 2)
        self.assertIn('Password reset email worker iteration failed.', '\n'.join(worker_logs.output))
        self.assertNotIn('token=', '\n'.join(worker_logs.output))

    def test_deleted_reset_job_during_failed_delivery_does_not_crash_worker(self):
        User.objects.create_user(
            email='alex@example.com', password=self.password, display_name='Alex'
        )
        self.start_reset('alex@example.com')

        def delete_then_fail(**_kwargs):
            PasswordResetEmailJob.objects.all().delete()
            raise OSError('temporary delivery failure')

        with patch('accounts.services.send_mail', side_effect=delete_then_fail):
            processed = self.deliver_queued_reset_emails()

        self.assertEqual(processed, 1)
        self.assertFalse(PasswordResetEmailJob.objects.exists())

    @override_settings(
        FRONTEND_PASSWORD_RESET_URL='https://app.example/reset-password?lang=en&source=email'
    )
    def test_reset_email_merges_uid_and_token_into_existing_query(self):
        User.objects.create_user(
            email='alex@example.com', password=self.password, display_name='Alex'
        )
        self.start_reset('alex@example.com')
        self.deliver_queued_reset_emails()

        reset_url = re.search(r'https://app\.example/reset-password\?[^\s]+', mail.outbox[0].body)
        query = parse_qs(urlparse(reset_url.group(0)).query)
        self.assertEqual(query['lang'], ['en'])
        self.assertEqual(query['source'], ['email'])
        self.assertTrue(query['uid'][0])
        self.assertTrue(query['token'][0])

    def test_password_reset_confirm_changes_password_and_invalidates_old_sessions(self):
        self.register()
        old_session_client = self.client
        self.client = Client(enforce_csrf_checks=True)
        self.start_reset('alex@example.com')
        self.deliver_queued_reset_emails()
        uid, token = self.reset_uid_and_token()

        response = self.confirm_reset(uid, token)

        self.assertEqual(response.status_code, 200, response.content)
        user = User.objects.get()
        self.assertTrue(user.check_password(self.new_password))
        self.assertEqual(old_session_client.get('/api/me/').status_code, 401)
        self.assertNotIn(token, response.content.decode())

    def test_login_is_rate_limited(self):
        User.objects.create_user(
            email='alex@example.com', password=self.password, display_name='Alex'
        )
        responses = [
            self.request_json('post', '/api/auth/login/', {
                'email': 'alex@example.com', 'password': 'wrong',
            })
            for _ in range(6)
        ]

        self.assertTrue(all(response.status_code == 400 for response in responses[:5]))
        self.assertEqual(responses[5].status_code, 429)

    def test_password_reset_is_rate_limited(self):
        responses = [
            self.request_json(
                'post', '/api/auth/password-reset/', {'email': 'missing@example.com'}
            )
            for _ in range(4)
        ]

        self.assertTrue(all(response.status_code == 200 for response in responses[:3]))
        self.assertEqual(responses[3].status_code, 429)

    def test_password_reset_rejects_invalid_token_and_weak_password(self):
        User.objects.create_user(
            email='alex@example.com', password=self.password, display_name='Alex'
        )
        self.start_reset('alex@example.com')
        self.deliver_queued_reset_emails()
        uid, token = self.reset_uid_and_token()

        invalid = self.confirm_reset(uid, 'invalid-token')
        weak = self.confirm_reset(uid, token, '123')

        self.assertEqual(invalid.status_code, 400)
        self.assertEqual(weak.status_code, 400)
        self.assertTrue(User.objects.get().check_password(self.password))

    def test_password_change_returns_401_without_authentication(self):
        response = self.request_json('post', '/api/auth/password-change/', {
            'current_password': 'anything', 'new_password': self.new_password,
        })

        self.assertEqual(response.status_code, 401)

    def test_password_change_requires_correct_current_password_and_keeps_session(self):
        self.register()
        invalid = self.request_json('post', '/api/auth/password-change/', {
            'current_password': 'wrong-current-password',
            'new_password': self.new_password,
        })
        self.assertEqual(invalid.status_code, 400)
        self.assertTrue(User.objects.get().check_password(self.password))

        changed = self.request_json('post', '/api/auth/password-change/', {
            'current_password': self.password,
            'new_password': self.new_password,
        })

        self.assertEqual(changed.status_code, 200)
        self.assertEqual(set(changed.json()), {'detail'})
        self.assertNotIn(self.new_password, changed.content.decode())
        self.assertNotIn(self.password, changed.content.decode())
        self.assertEqual(self.client.get('/api/me/').status_code, 200)
        other_client = Client(enforce_csrf_checks=True)
        self.client = other_client
        old_login = self.request_json('post', '/api/auth/login/', {
            'email': 'alex@example.com', 'password': self.password,
        })
        new_login = self.request_json('post', '/api/auth/login/', {
            'email': 'alex@example.com', 'password': self.new_password,
        })
        self.assertEqual(old_login.status_code, 400)
        self.assertEqual(new_login.status_code, 200)

    def test_password_change_throttle_is_keyed_per_user(self):
        first_user = User.objects.create_user(
            email='second@example.com', password=self.password, display_name='Second'
        )
        self.register()
        first_client = self.client
        second_client = Client(enforce_csrf_checks=True)
        second_client.force_login(first_user)

        def wrong_password_response(client):
            client.get('/api/auth/csrf/')
            token = client.cookies['csrftoken'].value
            return client.post(
                '/api/auth/password-change/',
                data=json.dumps({
                    'current_password': 'wrong-current-password',
                    'new_password': self.new_password,
                }),
                content_type='application/json',
                HTTP_X_CSRFTOKEN=token,
            )

        first_user_responses = [wrong_password_response(first_client) for _ in range(6)]
        second_user_response = wrong_password_response(second_client)

        self.assertTrue(all(response.status_code == 400 for response in first_user_responses[:5]))
        self.assertEqual(first_user_responses[5].status_code, 429)
        self.assertEqual(second_user_response.status_code, 400)

    def test_profile_and_password_change_share_the_user_throttle(self):
        self.register()
        profile_responses = [
            self.request_json('patch', '/api/me/', {
                'email': f'new-{index}@example.com',
                'current_password': 'wrong-current-password',
            })
            for index in range(3)
        ]
        password_responses = [
            self.request_json('post', '/api/auth/password-change/', {
                'current_password': 'wrong-current-password',
                'new_password': self.new_password,
            })
            for _ in range(3)
        ]

        self.assertTrue(all(response.status_code == 400 for response in profile_responses))
        self.assertEqual([response.status_code for response in password_responses], [400, 400, 429])

    def test_x_forwarded_for_cannot_bypass_ip_throttle_when_proxy_count_is_zero(self):
        responses = []
        for index in range(4):
            self.client.get('/api/auth/csrf/')
            token = self.client.cookies['csrftoken'].value
            responses.append(self.client.post(
                '/api/auth/password-reset/',
                data=json.dumps({'email': 'missing@example.com'}),
                content_type='application/json',
                HTTP_X_CSRFTOKEN=token,
                HTTP_X_FORWARDED_FOR=f'198.51.100.{index + 1}',
            ))

        self.assertEqual([response.status_code for response in responses], [200, 200, 200, 429])
