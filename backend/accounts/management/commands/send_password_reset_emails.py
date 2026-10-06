import logging
import time

from django.core.management.base import BaseCommand, CommandError

from accounts.services import process_password_reset_email_jobs

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Deliver queued password-reset emails and retry transient failures.'

    def add_arguments(self, parser):
        parser.add_argument('--once', action='store_true', help='Process one batch and exit.')
        parser.add_argument('--batch-size', type=int, default=10)
        parser.add_argument('--poll-interval', type=float, default=5)

    def handle(self, *args, **options):
        batch_size = options['batch_size']
        poll_interval = options['poll_interval']
        if batch_size < 1:
            raise CommandError('--batch-size must be greater than zero.')
        if poll_interval <= 0:
            raise CommandError('--poll-interval must be greater than zero.')

        while True:
            try:
                processed = process_password_reset_email_jobs(batch_size=batch_size)
            except Exception:
                logger.exception('Password reset email worker iteration failed.')
                if options['once']:
                    self.stderr.write('Password reset email batch failed.')
                    return
                time.sleep(poll_interval)
                continue
            if options['once']:
                self.stdout.write(f'Processed {processed} password-reset email job(s).')
                return
            if processed == 0:
                time.sleep(poll_interval)
