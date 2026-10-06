from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ('accounts', '0002_auththrottlecacheentry_passwordresetemailjob'),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name='user',
            name='accounts_user_email_ci_uniq',
        ),
    ]
