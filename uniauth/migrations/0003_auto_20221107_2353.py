# Generated by Django 3.1.5 on 2022-11-07 23:53

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("uniauth", "0002_auto_20190707_2305"),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name="institutionaccount",
            unique_together={("institution", "cas_id")},
        ),
    ]
