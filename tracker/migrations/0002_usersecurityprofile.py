from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('tracker', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='UserSecurityProfile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('question_1', models.CharField(max_length=20, choices=[
                    ('fav_food', "What is your favorite food?"),
                    ('mothers_maiden', "What is your mother's maiden name?"),
                    ('childhood_pet', "What was the name of your first pet?"),
                    ('birth_city', "In what city were you born?"),
                    ('fathers_bday', "What is your father's birthday? (e.g. Jan 1)"),
                    ('mothers_bday', "What is your mother's birthday? (e.g. Jan 1)"),
                    ('first_school', "What was the name of your first school?"),
                    ('fav_teacher', "What is the name of your favorite teacher?"),
                    ('childhood_hero', "Who was your childhood hero?"),
                    ('custom', "Custom question (write your own)"),
                ])),
                ('custom_question_1', models.CharField(blank=True, max_length=200, null=True)),
                ('answer_1_hash', models.CharField(max_length=64)),
                ('question_2', models.CharField(max_length=20, choices=[
                    ('fav_food', "What is your favorite food?"),
                    ('mothers_maiden', "What is your mother's maiden name?"),
                    ('childhood_pet', "What was the name of your first pet?"),
                    ('birth_city', "In what city were you born?"),
                    ('fathers_bday', "What is your father's birthday? (e.g. Jan 1)"),
                    ('mothers_bday', "What is your mother's birthday? (e.g. Jan 1)"),
                    ('first_school', "What was the name of your first school?"),
                    ('fav_teacher', "What is the name of your favorite teacher?"),
                    ('childhood_hero', "Who was your childhood hero?"),
                    ('custom', "Custom question (write your own)"),
                ])),
                ('custom_question_2', models.CharField(blank=True, max_length=200, null=True)),
                ('answer_2_hash', models.CharField(max_length=64)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='security_profile',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
        ),
    ]
