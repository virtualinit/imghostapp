# Generated by Django 4.0.4 on 2022-05-17 21:20

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('imagehostingapp', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='uploadedimages',
            name='image_temp_uri',
            field=models.URLField(default='', max_length=255, verbose_name='Image Temp URI'),
        ),
        migrations.AlterField(
            model_name='uploadedimages',
            name='image_created_at',
            field=models.DateTimeField(default=django.utils.timezone.now),
        ),
        migrations.AlterField(
            model_name='uploadedimages',
            name='image_uri_expiry_sec',
            field=models.IntegerField(default=-1, verbose_name='Image temp link expire after seconds'),
        ),
    ]