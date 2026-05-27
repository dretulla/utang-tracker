from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tracker', '0004_transaction_promise_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='transactionpayment',
            name='paid_time',
            field=models.TimeField(blank=True, null=True),
        ),
    ]
