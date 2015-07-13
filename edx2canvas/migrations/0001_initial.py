# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='CanvasApiAuthorization',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('lti_user_id', models.CharField(unique=True, max_length=255, db_index=True)),
                ('canvas_api_token', models.CharField(max_length=255)),
            ],
        ),
        migrations.CreateModel(
            name='EdxCourse',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('title', models.CharField(max_length=255)),
                ('org', models.CharField(max_length=128)),
                ('course', models.CharField(max_length=32)),
                ('run', models.CharField(max_length=32)),
                ('key_version', models.IntegerField()),
            ],
        ),
    ]
