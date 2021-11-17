import datetime

from django.db import models


class Post(models.Model):
    title = models.CharField(max_length=120, null=False)
    short_description = models.CharField(max_length=120, null=False)
    content = models.TextField(null=False)
    dt_created = models.DateField(null=False, default=datetime.date.today)

