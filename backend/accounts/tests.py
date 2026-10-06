import json
import re
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

from asgiref.sync import sync_to_async
from django.contrib.auth import aauthenticate, authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.cache import cache
from django.core import mail
from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.db import IntegrityError, transaction
from django.test import Client, SimpleTestCase, TestCase, override_settings

from accounts.models import User
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
            default_email_backend,
            parse_csrf_trusted_origins,
            parse_secure_proxy_ssl_header,
        )

        self.assertEqual(
            parse_secure_proxy_ssl_header('true'),
            ('HTTP_X_FORWARDED_PROTO', 'https'),
        )
        self.assertIsNone(parse_secure_proxy_ssl_header('false'))
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

        self.assertIn('rest_framework.throttling.ScopedRateThrottle', settings.REST_FRAMEWORK[
            'DEFAULT_THROTTLE_CLASSES'
        ])
        self.assertEqual(settings.REST_FRAMEWORK['DEFAULT_THROTTLE_RATES']['login'], '5/minute')
        self.assertEqual(settings.REST_FRAMEWORK['DEFAULT_THROTTLE_RATES']['password_reset'], '3/hour')
        self.assertGreater(settings.EMAIL_TIMEOUT, 0)


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
        self.assertIn('email', response.json())
        self.assertEqual(User.objects.count(), 1)

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

    def test_display_name_change_does_not_require_current_password(self):
        self.register()

        response = self.request_json('patch', '/api/me/', {'display_name': 'New Name'})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(User.objects.get().display_name, 'New Name')

    def test_registration_validates_password_only_once(self):
        from django.contrib.auth.password_validation import validate_password

        with patch('accounts.services.validate_password', wraps=validate_password) as validate:
            response = self.register()

        self.assertEqual(response.status_code, 201)
        self.assertEqual(validate.call_count, 1)

    def test_protected_profile_returns_401_without_authentication(self):
        response = self.client.get('/api/me/')

        self.assertEqual(response.status_code, 401)

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
        self.reset_email_jobs = []
        self.submit_patcher = patch(
            'accounts.services.password_reset_email_executor.submit',
            side_effect=lambda function, *args: self.reset_email_jobs.append((function, args)),
        )
        self.submit_patcher.start()
        self.addCleanup(self.submit_patcher.stop)

    def deliver_queued_reset_emails(self):
        queued, self.reset_email_jobs = self.reset_email_jobs, []
        for function, args in queued:
            function(*args)

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
        with patch('accounts.services.send_mail') as deliver:
            response = self.start_reset('alex@example.com')
            self.assertEqual(response.status_code, 200)
            deliver.assert_not_called()
            self.assertEqual(len(self.reset_email_jobs), 1)
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
        reset_link = self.reset_email_jobs[0][1][1]
        token = parse_qs(urlparse(reset_link).query)['token'][0]

        with patch(
            'accounts.services.send_mail',
            side_effect=OSError(f'SMTP unavailable while sending token {token}'),
        ), self.assertLogs('accounts.services', level='ERROR') as delivery_logs:
            self.deliver_queued_reset_emails()

        self.assertTrue(any('SMTP unavailable' in entry for entry in delivery_logs.output))
        self.assertNotIn(token, '\n'.join(delivery_logs.output))

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
