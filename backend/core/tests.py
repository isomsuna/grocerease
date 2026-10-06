from django.conf import settings
from django.test import SimpleTestCase


class BackendSmokeTests(SimpleTestCase):
    def test_health_endpoint_returns_ok_without_caching(self):
        response = self.client.get('/api/health/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'status': 'ok'})
        self.assertEqual(response['Cache-Control'], 'no-store')

    def test_application_timezone_is_manila(self):
        self.assertEqual(settings.TIME_ZONE, 'Asia/Manila')
