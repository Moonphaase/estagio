from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api_keys', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='apikey',
            name='key_full',
            field=models.CharField(blank=True, max_length=128),
        ),
    ]
