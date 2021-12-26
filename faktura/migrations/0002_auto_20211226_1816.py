# Generated by Django 3.2.10 on 2021-12-26 18:16

import django.core.validators
from django.db import migrations, models
import django.db.models.deletion
import faktura.models
import faktura.validators
import uuid
from faktura.settings import DEFAULT_ACCOUNT


def create_default_account(apps, schema_editor):
    # We can't import the Person model directly as it may be a newer
    # version than this migration expects. We use the historical version.
    account = apps.get_model('faktura', 'Account')

    if DEFAULT_ACCOUNT:
        account.objects.get_or_create(title=DEFAULT_ACCOUNT)


class Migration(migrations.Migration):

    dependencies = [
        ('faktura', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Account',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('title', models.CharField(max_length=255, verbose_name='Title')),
                ('description', models.TextField(blank=True, null=True, verbose_name='Description')),
                ('metadata', models.JSONField(blank=True, help_text='Metadata about Account.', null=True, verbose_name='Metadata')),
            ],
        ),
        migrations.CreateModel(
            name='Transaction',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('date', models.DateField(verbose_name='Date')),
                ('title', models.CharField(blank=True, max_length=255, null=True, verbose_name='Title')),
                ('description', models.TextField(blank=True, null=True, verbose_name='Description')),
                ('type', models.CharField(choices=[('income', 'Income'), ('expense', 'Expense'), ('asset', 'Asset'), ('liability', 'Liability')], default='expense', max_length=12, verbose_name='Typ')),
                ('amount', models.FloatField(verbose_name='Amount')),
                ('currency', models.CharField(default='EUR', max_length=4, verbose_name='Mena')),
                ('metadata', models.JSONField(blank=True, help_text='Metadata about transaction.', null=True, verbose_name='Metadata')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('account', models.ForeignKey(default=faktura.models.get_default_account, on_delete=django.db.models.deletion.CASCADE, to='faktura.account')),
                ('link', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='faktura.transaction', verbose_name='Account link')),
            ],
        ),
        migrations.CreateModel(
            name='Document',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('title', models.CharField(blank=True, max_length=255, null=True, verbose_name='Title')),
                ('description', models.TextField(blank=True, null=True, verbose_name='Description')),
                ('metadata', models.JSONField(blank=True, help_text='Metadata about document.', null=True, verbose_name='Metadata')),
                ('data', models.FileField(blank=True, help_text='Upload proof of your work (document, video, image).', null=True, upload_to='accounting', validators=[django.core.validators.FileExtensionValidator(['jpg', 'jpeg', 'png', 'pdf', 'doc', 'docx', 'txt', 'xls', 'xlsx']), faktura.validators.FileSizeValidator(10)], verbose_name='Data')),
                ('invoice', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='transactions', related_query_name='transaction', to='faktura.invoice')),
                ('transaction', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='documents', related_query_name='document', to='faktura.transaction')),
            ],
        ),
        migrations.RunPython(create_default_account),
    ]
