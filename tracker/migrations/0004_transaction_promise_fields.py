from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tracker', '0003_transaction_time_transactionitem_unit'),
    ]

    operations = [
        migrations.AddField(
            model_name='transaction',
            name='promise_date',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='transaction',
            name='promise_time',
            field=models.TimeField(blank=True, null=True),
        ),
    ]
