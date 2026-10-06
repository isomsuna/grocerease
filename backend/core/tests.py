from django.conf import settings
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import SimpleTestCase, TransactionTestCase


class BackendSmokeTests(SimpleTestCase):
    def test_health_endpoint_returns_ok_without_caching(self):
        response = self.client.get('/api/health/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'status': 'ok'})
        self.assertEqual(response['Cache-Control'], 'no-store')

    def test_application_timezone_is_manila(self):
        self.assertEqual(settings.TIME_ZONE, 'Asia/Manila')


class MigrationReversibilityTests(TransactionTestCase):
    def test_all_migrations_can_be_rolled_back_and_reapplied(self):
        executor = MigrationExecutor(connection)
        latest = executor.loader.graph.leaf_nodes()

        executor.migrate([(app_label, None) for app_label, _ in latest])
        executor.loader.build_graph()
        self.assertEqual(executor.loader.applied_migrations, {})

        executor.migrate(latest)
        executor.loader.build_graph()
        self.assertEqual(executor.migration_plan(latest), [])
