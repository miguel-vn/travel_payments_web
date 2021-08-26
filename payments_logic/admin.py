from django.contrib import admin

from .models import Payment, Person, Travel

admin.site.register(Payment)
admin.site.register(Person)
admin.site.register(Travel)
